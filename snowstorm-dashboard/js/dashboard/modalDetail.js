import { AJAX_TIMEOUT_MS } from './constants.js';
import { fetchWithTimeout } from './http.js';

const PREVIEW_LIMIT = 30;

function asText(value, fallback = 'N/A') {
	if (value == null) return fallback;
	const text = String(value).trim();
	return text === '' ? fallback : text;
}

function flattenConcepts(concepts, depth = 0, out = []) {
	if (!Array.isArray(concepts)) return out;
	for (const concept of concepts) {
		out.push({
			code: asText(concept.code, ''),
			display: asText(concept.display, ''),
			definition: asText(concept.definition, ''),
			depth
		});
		if (out.length >= PREVIEW_LIMIT) return out;
		flattenConcepts(concept.concept, depth + 1, out);
		if (out.length >= PREVIEW_LIMIT) return out;
	}
	return out;
}

function conceptMapRows(groups, limit = PREVIEW_LIMIT) {
	const rows = [];
	if (!Array.isArray(groups)) return rows;
	for (const group of groups) {
		const elements = Array.isArray(group.element) ? group.element : [];
		for (const element of elements) {
			const targets = Array.isArray(element.target) && element.target.length ? element.target : [{}];
			for (const target of targets) {
				rows.push({
					sourceSystem: asText(group.source, ''),
					targetSystem: asText(group.target, ''),
					sourceCode: asText(element.code, ''),
					sourceDisplay: asText(element.display, ''),
					targetCode: asText(target.code, ''),
					targetDisplay: asText(target.display, ''),
					equivalence: asText(target.equivalence, '')
				});
				if (rows.length >= limit) return rows;
			}
		}
	}
	return rows;
}

function countConceptMapTargets(groups) {
	if (!Array.isArray(groups)) return 0;
	return groups.reduce((sum, group) => {
		const elements = Array.isArray(group.element) ? group.element : [];
		return sum + elements.reduce((inner, element) => {
			const targets = Array.isArray(element.target) ? element.target.length : 0;
			return inner + Math.max(targets, 1);
		}, 0);
	}, 0);
}

function relationTokens(detail) {
	const stopTokens = new Set(['http', 'https', 'www', 'org', 'com', 'info', 'fhir', 'terminology', 'codesystem', 'valueset']);
	return [
		detail.name,
		detail.title,
		detail.url
	]
		.filter(Boolean)
		.flatMap(value => String(value).split(/[^a-zA-Z0-9]+/))
		.map(token => token.toLowerCase().replace(/codesystem|valueset|conceptmap/g, ''))
		.filter(token => token.length >= 4 && !stopTokens.has(token));
}

function rowMatchesTokens(row, tokens) {
	const haystack = `${row.title || ''} ${row.url || ''}`.toLowerCase();
	return tokens.some(token => haystack.includes(token));
}

function firstUsableCodeRow(rows, systemUrl = '') {
	if (!Array.isArray(rows)) return null;
	return rows.find(row => {
		const code = asText(row.code, '');
		const system = asText(row.system, '');
		return code && (!systemUrl || system === systemUrl);
	}) || null;
}

export const dashboardModalDetail = {
	async viewDetail(type, id) {
		this.modalType = type;
		this.modalLoading = true;
		this.modalDetail = null;
		this.modalError = null;
		const modalEl = document.getElementById(type + 'Modal');
		const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
		modal.show();

		const url = `${this.fhirBaseUrl}/${type === 'codesystem' ? 'CodeSystem' : type === 'valueset' ? 'ValueSet' : 'ConceptMap'}/${id}`;
		let res;
		try {
			res = await fetchWithTimeout(url, AJAX_TIMEOUT_MS);
			const data = await res.json();
			if (!res.ok) throw new Error(data.message || 'Not found');
			this.modalDetail = data;
			if (type === 'codesystem' && this.modalDetail) {
				await this.enrichCodeSystemDetail(this.modalDetail);
			}
			if (type === 'valueset' && this.modalDetail) {
				await this.enrichValueSetDetail(this.modalDetail);
			}
			if (type === 'conceptmap' && this.modalDetail) {
				this.enrichConceptMapDetail(this.modalDetail);
			}
		} catch (err) {
			if (err.name === 'AbortError') this.modalError = 'Request timed out. Please try again.';
			else if (typeof res !== 'undefined' && res.status === 404) this.modalError = `${type === 'codesystem' ? 'CodeSystem' : type === 'valueset' ? 'ValueSet' : 'ConceptMap'} not found.`;
			else if (typeof res !== 'undefined' && res.status === 500) this.modalError = 'Server error. Please try again later.';
			else this.modalError = err.message || 'Error loading details';
		} finally {
			this.modalLoading = false;
		}
	},

	async enrichCodeSystemDetail(detail) {
		if ((!this.valueSets || this.valueSets.length === 0) && !this.loadingValueSets) {
			await this.loadValueSets();
		}
		if ((!this.conceptMaps || this.conceptMaps.length === 0) && !this.loadingConceptMaps) {
			await this.loadConceptMaps();
		}
		const concepts = Array.isArray(detail.concept) ? detail.concept : [];
		const systemUrl = asText(detail.url, '');
		detail.previewConcepts = flattenConcepts(concepts);
		detail.previewConceptTotal = concepts.length;

		const [fullValueSets, fullConceptMaps] = await Promise.all([
			this._getFullValueSets(),
			this._getFullConceptMaps()
		]);
		detail.previewValueSets = fullValueSets.filter(vs =>
			systemUrl && ((vs.compose && vs.compose.include) || []).some(inc => inc.system === systemUrl)
		).slice(0, 8);
		detail.previewConceptMaps = fullConceptMaps.filter(cm =>
			systemUrl && (cm.group || []).some(g => g.source === systemUrl || g.target === systemUrl)
		).slice(0, 8);

		detail.previewCodeSamples = detail.previewConcepts
			.filter(concept => concept.code)
			.map(concept => ({
				system: systemUrl,
				code: concept.code,
				display: concept.display
			}))
			.slice(0, PREVIEW_LIMIT);
		if (!detail.previewCodeSamples.length) {
			detail.previewCodeSamples = await this.loadCodeSystemSamplesFromValueSets(detail);
		}
	},

	async loadCodeSystemSamplesFromValueSets(detail) {
		const systemUrl = asText(detail.url, '');
		const samples = [];
		for (const vs of detail.previewValueSets || []) {
			if (!vs.url || samples.length >= PREVIEW_LIMIT) break;
			try {
				const qs = new URLSearchParams();
				qs.append('url', vs.url);
				qs.append('_count', String(PREVIEW_LIMIT));
				const res = await fetchWithTimeout(`${this.fhirBaseUrl}/ValueSet/$expand?${qs.toString()}`, AJAX_TIMEOUT_MS);
				const data = await res.json();
				if (!res.ok) continue;
				const contains = Array.isArray(data.expansion?.contains) ? data.expansion.contains : [];
				for (const item of contains) {
					if (asText(item.system, '') !== systemUrl || !asText(item.code, '')) continue;
					samples.push({
						system: asText(item.system, ''),
						code: asText(item.code, ''),
						display: asText(item.display, '')
					});
					if (samples.length >= PREVIEW_LIMIT) break;
				}
			} catch {
				// Keep the modal usable when a related ValueSet cannot be expanded.
			}
		}
		return samples;
	},

	async enrichValueSetDetail(detail) {
		detail.previewIncludes = Array.isArray(detail.compose?.include) ? detail.compose.include : [];
		detail.previewExpansionRows = [];
		detail.previewExpansionTotal = null;
		detail.previewExpansionError = null;
		const canonicalUrl = asText(detail.url, '');
		if (!canonicalUrl) return;
		try {
			const qs = new URLSearchParams();
			qs.append('url', canonicalUrl);
			qs.append('_count', String(PREVIEW_LIMIT));
			const res = await fetchWithTimeout(`${this.fhirBaseUrl}/ValueSet/$expand?${qs.toString()}`, AJAX_TIMEOUT_MS);
			const data = await res.json();
			if (!res.ok) throw new Error(data.message || data.issue?.[0]?.diagnostics || 'Expansion failed');
			const contains = Array.isArray(data.expansion?.contains) ? data.expansion.contains : [];
			detail.previewExpansionRows = contains.map(item => ({
				system: asText(item.system, ''),
				code: asText(item.code, ''),
				display: asText(item.display, '')
			}));
			detail.previewValidateCode = firstUsableCodeRow(detail.previewExpansionRows);
			detail.previewExpansionTotal = data.expansion?.total ?? contains.length;
		} catch (err) {
			detail.previewExpansionError = err.name === 'AbortError'
				? 'Expansion timed out.'
				: (err.message || 'Expansion unavailable.');
		}
	},

	enrichConceptMapDetail(detail) {
		const groups = Array.isArray(detail.group) ? detail.group : [];
		const g0 = groups.length ? groups[0] : null;
		if (g0) {
			if (g0.source != null && String(g0.source).trim() !== '') {
				detail.sourceCodeSystem = g0.source;
			}
			if (g0.target != null && String(g0.target).trim() !== '') {
				detail.targetCodeSystem = g0.target;
			}
		}
		if (!detail.fullUrl && detail.id) {
			detail.fullUrl = `${this.fhirBaseUrl}/ConceptMap/${encodeURIComponent(detail.id)}`;
		}
		detail.previewGroups = groups.map((group, index) => ({
			index: index + 1,
			source: asText(group.source, ''),
			target: asText(group.target, ''),
			elementCount: Array.isArray(group.element) ? group.element.length : 0,
			targetCount: countConceptMapTargets([group])
		}));
		detail.previewMapRows = conceptMapRows(groups);
		detail.previewMapTotal = countConceptMapTargets(groups);
	},

	formatPreviewCount(total, shown) {
		if (total == null) return `${shown}`;
		return total > shown ? `${shown} of ${total}` : `${total}`;
	},

	openValueSetExpandExample() {
		const url = asText(this.modalDetail?.url, '');
		if (!url) return;
		const qs = new URLSearchParams();
		qs.append('url', url);
		qs.append('_count', '50');
		window.open(`${this.fhirBaseUrl}/ValueSet/$expand?${qs.toString()}`, '_blank', 'noopener,noreferrer');
	},

	openValueSetValidateExample() {
		const url = asText(this.modalDetail?.url, '');
		const sample = this.modalDetail?.previewValidateCode;
		if (!url || !sample?.system || !sample?.code) {
			alert('This ValueSet needs an expanded code sample to open a validate-code example.');
			return;
		}
		const qs = new URLSearchParams();
		qs.append('url', url);
		qs.append('system', sample.system);
		qs.append('code', sample.code);
		window.open(`${this.fhirBaseUrl}/ValueSet/$validate-code?${qs.toString()}`, '_blank', 'noopener,noreferrer');
	},

	openCodeSystemLookupExample() {
		const system = asText(this.modalDetail?.url, '');
		const sample = this.modalDetail?.previewCodeSamples?.[0];
		if (!system || !sample?.code) {
			alert('This CodeSystem needs a code sample to open a lookup example.');
			return;
		}
		const qs = new URLSearchParams();
		qs.append('system', system);
		qs.append('code', sample.code);
		window.open(`${this.fhirBaseUrl}/CodeSystem/$lookup?${qs.toString()}`, '_blank', 'noopener,noreferrer');
	},

	openCodeSystemValidateExample() {
		const url = asText(this.modalDetail?.url, '');
		const sample = this.modalDetail?.previewCodeSamples?.[0];
		if (!url || !sample?.code) {
			alert('This CodeSystem needs a code sample to open a validate-code example.');
			return;
		}
		const qs = new URLSearchParams();
		qs.append('url', url);
		qs.append('code', sample.code);
		window.open(`${this.fhirBaseUrl}/CodeSystem/$validate-code?${qs.toString()}`, '_blank', 'noopener,noreferrer');
	},

	openCodeSystemSubsumesExample() {
		const system = asText(this.modalDetail?.url, '');
		const samples = this.modalDetail?.previewCodeSamples || [];
		if (!system || samples.length < 2 || !samples[0]?.code || !samples[1]?.code) {
			alert('This CodeSystem needs two code samples to open a subsumes example.');
			return;
		}
		const qs = new URLSearchParams();
		qs.append('system', system);
		qs.append('codeA', samples[0].code);
		qs.append('codeB', samples[1].code);
		window.open(`${this.fhirBaseUrl}/CodeSystem/$subsumes?${qs.toString()}`, '_blank', 'noopener,noreferrer');
	},

	async openConceptMapTranslateExample() {
		const fullUrl = this.modalDetail?.fullUrl;
		if (!fullUrl) return;
		this.conceptMapTranslateExampleBusy = true;
		let res;
		try {
			res = await fetchWithTimeout(fullUrl, AJAX_TIMEOUT_MS);
			const data = await res.json();
			if (!res.ok) throw new Error(data.message || 'Failed to load ConceptMap');
			const mapUrl = data.url != null ? String(data.url).trim() : '';
			const g0 = Array.isArray(data.group) && data.group.length ? data.group[0] : null;
			const system = g0 && g0.source != null ? String(g0.source).trim() : '';
			const el0 = g0 && Array.isArray(g0.element) && g0.element.length ? g0.element[0] : null;
			const code = el0 && el0.code != null ? String(el0.code).trim() : '';
			if (!mapUrl || !system || !code) {
				alert(
					'This ConceptMap needs a canonical url, at least one group with source, and at least one element with code to open a translate example.'
				);
				return;
			}
			const qs = new URLSearchParams();
			qs.append('code', code);
			qs.append('system', system);
			qs.append('url', mapUrl);
			const path = `/ConceptMap/$translate?${qs.toString()}`;
			window.open(`${this.fhirBaseUrl}${path}`, '_blank', 'noopener,noreferrer');
		} catch (err) {
			if (err.name === 'AbortError') alert('Request timed out. Please try again.');
			else alert(err.message || 'Failed to open translate example');
		} finally {
			this.conceptMapTranslateExampleBusy = false;
		}
	}
};
