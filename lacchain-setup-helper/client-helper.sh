# !/bin/bash
########### Create a Self Signed Certificate ###########
function createRSASelfSignedCertificate() {
    echo
    echo "*********Starting RSA Self Signed Certificate creation process **********"
    echo
    # SCA
    mkdir -p certs/SCA
    if [[ $(ls certs/SCA | wc -l) > 0 ]]; then
        while true; do
            echo "Certificates found on certs/SCA, do you want to override these? (Y/N):  "
            echo -n "> "
            read continue
            if [[ ("$continue" != "y") && ("$continue" != "yes") && ("$continue" != "Y") && ("$continue" != "YES") ]]; then
                echo "exiting ..."
                return
            else
                echo "Ok, lets start creating a new Self Signed Certificate"
                break
            fi
        done
    fi
    create=false
    while true; do
        echo "Enter country code for your Signed Certificate; example: PE ...(see more codes on: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)"
        # echo "press enter to skip this step"
        echo -n "> "
        read country
        sleep 0.1

        echo "Enter State; example: LMA ... (e.g. see more state codes on: https://en.wikipedia.org/wiki/ISO_3166-2:PE)"
        echo "press enter to skip this step"
        echo -n "> "
        read state
        sleep 0.1

        echo "Enter your organization name; example: Ministry Of Health Of Peru"
        echo -n "> "
        read organizationName
        sleep 0.1

        echo "Enter a common name; example: Peru_MoH"
        echo "press enter to skip this step"
        echo -n "> "
        read commonName
        sleep 0.1

        echo
        echo "You specified: "
        echo "Country: '$country'; State: '$state', Organization: '$organizationName', Common Name: '$commonName'"

        echo "Please keep in mind that if you didn't specify a valid Country code you will probably get an error"
        echo
        echo "Please confirm to continue (Y/N): "
        echo
        echo -n "> "
        read continue
        echo
        if [[ ("$continue" != "y") && ("$continue" != "yes") && ("$continue" != "Y") && ("$continue" != "YES") ]]; then
            echo "Do you want to change the values (Y/N): "
            echo
            echo -n "> "
            read change
            echo
            if [[ ("$change" != "y") && ("$change" != "yes") && ("$change" != "Y") && ("$change" != "YES") ]]; then
                echo "Cancelling X509 Self Signed Certificate creation"
                break
            else
                echo "No problem ... Let's enter the values again..."
            fi
        else
            echo "Proceeding to create Self Signed Certificate"
            create=true
            break
        fi
    done

    if [[ "$create" == false ]]; then
        return
    fi

    # echo $state
    openssl genrsa -out "certs/SCA/SCA.key" 4096
    openssl req -x509 -new -nodes -key "certs/SCA/SCA.key" -subj "/C=$country/ST=$state/O=$organizationName/CN=$commonName" -sha512 -days 1440 -out "certs/SCA/SCA.crt"

    # Request CSR
    mkdir -p certs/DSC
    openssl genrsa -out "certs/DSC/DSC.key" 2048
    openssl req -new -sha512 -key "certs/DSC/DSC.key" -subj "/C=$country/ST=$state/O=$organizationName/CN=$commonName" -out "certs/DSC/DSC.csr"

    # Sign
    openssl x509 -req -in "certs/DSC/DSC.csr" -CA "certs/SCA/SCA.crt" -CAkey "certs/SCA/SCA.key" -CAcreateserial -extensions v3_req -extfile "openssl.cnf" -out "certs/DSC/DSC.crt" -days 500 -sha512

    echo Certificates were created successfully inside folder "'./certs'"
}

######################### DID ##########################
function createDid() {
    create_did_url="$api_url"/api/v1/did/lac1
    r=$(curl -s -X 'POST' \
        ${create_did_url} \
        -H 'accept: application/json' \
        -d '')

    did=$(echo $r | sed 's/^{"did":"//' | sed 's/"}$//')
    if [[ $did == *"did:"* ]]; then
        echo "Saving did to did.txt file"
        echo $did >did.txt
        echo "Did was created: $did"
    else
        echo "there was an error creating the did, please check your service"
    fi
}

function createDidAndSaveToFile() {
    echo
    echo "*********Starting DID creation process**********"
    echo
    if [ -f "did.txt" ]; then
        echo "A did.txt file already exists, do you want to overwrite it? (y/n)"
        echo
        echo -n "> "
        read isToBeOverridden
        echo
        if [[ ("$isToBeOverridden" != "y") && ("$isToBeOverridden" != "yes") && ("$isToBeOverridden" != "Y") && ("$isToBeOverridden" != "YES") ]]; then
            echo "cancelling operation, bye ..."
            sleep 2
        else
            echo overriding did.txt with new content
            createDid
        fi
    else
        createDid
    fi
    echo
}

############ Signing Certs ###########
function addX509Certificate() {
    echo
    echo "*********Starting X509/DID association process**********"
    echo
    echo "Please enter the path to the x509 Signing Certificate, must be something like: ./certs/DSC/DSC.crt " #todo save path to consume later
    echo
    echo -n "> "
    read path_to_crt
    echo
    if [ -f $path_to_crt ]; then
        echo "File found, stating the process ..."
        if [ -f "did.txt" ]; then
            did=$(cat did.txt | sed 's/^{"did":"//' | sed 's/"}$//')
            echo Associating $did to certificate file
            # process
            add_pem_certificate_url="$api_url"/api/v1/did/lac1/attribute/add/jwk-from-x509certificate
            relation=asse
            data="{\"did\":\"$did\", \"relation\":\"$relation\"}"
            curl -X POST ${add_pem_certificate_url} -H "accept: application/json" -F x509Cert=@$path_to_crt -F data="$data"
            echo
            echo "done!, X509 certificate was successfully associated to did"
            echo
        else
            echo "Could not find any did at ./did.txt ..."
            echo You many need to create a did
            echo If you have the did.txt file in another location just bring it to this location.
        fi
    else
        echo "No file was found at the specified path ... exiting"
    fi
    echo
}

function revokex59Certificate() {
    echo
    echo "*********Starting X509/DID disassociation process**********"
    echo
    echo "Please enter the path to the x509 Signing Certificate, must be something like: ./certs/DSC/DSC.crt"
    echo
    echo -n "> "
    read path_to_crt
    echo
    if [ -f $path_to_crt ]; then
        echo "File found, stating the process ..."
        if [ -f "did.txt" ]; then
            did=$(cat did.txt | sed 's/^{"did":"//' | sed 's/"}$//')
            echo found did is $did ...

            compromised=false
            echo "Enter backward revocation days, must be a zero or positive number"
            echo
            echo -n "> "
            read backwardRevocationDays
            echo
            echo Starting disassociation process ...
            # process
            disassociate_pem_certificate_url="$api_url"/api/v1/did/lac1/attribute/revoke/jwk-from-x509certificate
            relation=asse
            data='{"did":'"\"$did\""', "relation":'"\"$relation\""', "compromised":'$compromised', "backwardRevocationDays":'$backwardRevocationDays'}'
            curl -X 'DELETE' ${disassociate_pem_certificate_url} -H 'accept: application/json' -F x509Cert=@$path_to_crt -F data="$data"
            echo
            echo "done!, X509 certificate was removed from did"
            echo
        else
            echo "Could not find any did at ./did.txt ..."
            echo You many need to create a did
            echo If you have the did.txt file in another location just bring it to this location.
        fi
    else
        echo "No file was found at the specified path ... exiting"
    fi
    echo
}

######################### CHAIN OF TRUST ##########################

function createManager() {
    echo
    echo "*********Starting Manager creation process**********"
    echo
    manager_url="$api_url"/api/v1/manager
    if [ -f "did.txt" ]; then
        did=$(cat did.txt | sed 's/^{"did":"//' | sed 's/"}$//')

        echo Creating new manager and associatig to did $did

        echo "Please enter the amount of days in which the manager will be considered valid"
        echo
        echo -n "> "
        read validDays
        echo
        #validDays=100 # Number of days in which the manager to be created will be considered valid
        echo "creating a new manager for $validDays days"
        add_manager_url=$manager_url
        curl -X 'POST' \
            ${add_manager_url} \
            -H 'accept: application/json' \
            -H 'Content-Type: application/json' \
            -d '{
        "did": '\"$did\"',
        "validDays": '$validDays'
        }'
        echo
        echo "done!,new manager was created and will be valid for $validDays days."
        echo
    else
        echo "Could not find any did at ./did.txt ..."
        echo You many need to create a did
        echo If you have the did.txt file in another location just bring it to this location.
    fi
}

function getManager() {
    echo
    echo "*********Getting Manager **********"
    echo
    manager_url="$api_url"/api/v1/manager
    if [ -f "did.txt" ]; then
        did=$(cat did.txt | sed 's/^{"did":"//' | sed 's/"}$//')

        echo Getting current manager associated to did $did
        echo

        get_manager_url="$manager_url"/"$did"
        curl -X 'GET' \
            $get_manager_url \
            -H 'accept: application/json'

        echo
    else
        echo "Could not find any did at ./did.txt ..."
        echo You many need to create a did
        echo If you have the did.txt file in another location just bring it to this location.
    fi
}

############## CLI ##########

function actions() {
    while true; do
        sleep 0.5
        echo
        echo "************* CLI MAIN MENU *************"
        echo type "'CD'" to create a new did
        echo type "'CM'" to create a new chain of trust manager
        echo type "'GCM'" to get the current manager
        echo type "'exit'" to exit the program
        echo
        echo -n "> "
        read action
        echo
        case "${action}" in
        "SSC")
            createRSASelfSignedCertificate
            ;;
        "CD")
            createDidAndSaveToFile
            ;;
        "AX")
            addX509Certificate
            ;;
        "DX")
            revokex59Certificate
            ;;
        "CM")
            createManager
            ;;
        "GCM")
            getManager
            ;;
        "exit")
            echo "Exiting ... bye"
            echo
            break
            ;;
        *)
            echo "Please type a valid option"
            echo
            ;;
        esac
    done
}

echo
echo "*************************************************************************"
echo "****************** Wecome to the LACPass-Client Helper ******************"
echo "*************************************************************************"
echo
echo "Please enter the API URL to connect to, make sure it is something like http://localhost:3010"
echo -n "> "
read api_url
echo
if [[ $api_url == *"http"* ]]; then
    actions
else
    echo "Please check the api_url, that must be in the format, something like http://localhost:3010 but found ${api_url}"
fi
