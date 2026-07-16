# Device Monitoring Web App

This app displays daily (7 days a week) monitoring checks run by `../scheduled_device_monitoring.sh` on MSI. This app, and the Postgres database with which it interacts, are hosted on Google Cloud. The daily monitoring script pushes its data to this Postgres database.

The website for this app can be found [here](https://device-monitoring-web-711082233215.us-central1.run.app/). You will need to sign in with the lab's credentials.

## MSI Credentials Configuration
There are two sets of credentials you need to add to `~/.rtgs_creds`. The first needs to be added to the top of the file.

1. The first set of credentials needs to be added to the top of the file.
    1. Go to the `rtgs-lab-tools` directory and activate the virtual environment. Then run the command
        ~~~
        python -c "import certifi; print(certifi.where())"
        ~~~
    2. This should return a filepath. Copy this filepath and add the following two lines to the credentials file:
        ~~~
        export SSL_CERT_FILE=<filepath>
        export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
        ~~~
    3. If the previous command returned an error, then run `uv sync` to make sure that the required package has been installed. Then rerun the command.
2. The second set of credentials can be added anywhere in the file.
    ~~~
    export DEVICEMON_INSTANCE_CONNECTION_NAME=<database project name on Google Cloud>
    export DEVICEMON_DB_NAME=<database name>
    export DEVICEMON_DB_USER=<database username>
    export DEVICEMON_DB_PASSWORD=<database password>
    export GOOGLE_APPLICATION_CREDENTIALS=<path to device-monitoring-writer-key.json file>
    ~~~

## Updating the Web App
After making changes to your local version of the web app, you need to deploy those changes to Google Cloud Run.

1. In your terminal, navigate to the `rtgs-lab-tools/src/rtgs_lab_tools/device_monitoring/web_app` directory.
2. Run the following command:
    ~~~
    gcloud run deploy device-monitoring-web --source . --project sustained-edge-501900-p8 --region us-central1
    ~~~

## Changing the Username or Password

Notes:
1. You must do this in Git Bash or a Linux terminal, not Windows Powershell.
2. You need to have the `gcloud` CLI installed in your terminal.

### Changing the Username
Replace `<new_username>` with the new username.
~~~
gcloud run services update device-monitoring-web --project sustained-edge-501900-p8 --region us-central1 --update-env-vars=DEVICEMON_SITE_USERNAME=<new_username>
~~~

### Changing the Password
This takes multiple commands.

1. 
    ~~~
    read -s -p "Enter new site password: " NEWPW
    ~~~
    Press the enter key, then type in the new password. You won't be able to see it. Press enter when you're done.

2. Run the following commands one at a time. Press the enter key after each one. Some of them might take a bit of time to complete. Be patient.
    ~~~
    echo
    ~~~

    ~~~
    printf '%s' "$NEWPW" | gcloud secrets versions add rtgs-devicemon-site-password --project sustained-edge-501900-p8 --data-file=-
    ~~~

    ~~~
    unset NEWPW
    ~~~

3. Deploy the changes to the web app:
    ~~~
    gcloud run services update device-monitoring-web --project sustained-edge-501900-p8 --region us-central1 --update-secrets=DEVICEMON_SITE_PASSWORD=rtgs-devicemon-site-password:latest
    ~~~