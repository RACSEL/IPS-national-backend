function getErrorMessage(err, fallback) {
  const { data } = err.response || {};
  if (typeof data === 'string' && data.trim()) {
    return data;
  }
  if (data?.error) {
    return typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
  }
  if (data?.message) {
    return typeof data.message === 'string' ? data.message : JSON.stringify(data.message);
  }
  const issue = Array.isArray(data?.issue)
    ? data.issue.find((item) => item?.diagnostics || item?.details?.text)
    : null;
  if (issue?.diagnostics) {
    return issue.diagnostics;
  }
  if (issue?.details?.text) {
    return issue.details.text;
  }
  if (err.message) {
    return err.message;
  }
  return fallback;
}

function getErrorResponse(err, fallback, fallbackStatus = 500) {
  return {
    status: err.response?.status || fallbackStatus,
    body: {
      error: getErrorMessage(err, fallback),
    },
  };
}

module.exports = {
  getErrorMessage,
  getErrorResponse,
};
