# Device Monitoring Web App

This app displays daily (7 days a week) monitoring checks run by `../scheduled_device_monitoring.sh` on MSI. This app, and the Postgres database with which it interacts, are hosted on Google Cloud. The daily monitoring script pushes its data to this Postgres database.

The website for this app can be found [here](https://device-monitoring-web-711082233215.us-central1.run.app/). You will need to sign in with the lab's credentials.

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
This takes multiple commands. \

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