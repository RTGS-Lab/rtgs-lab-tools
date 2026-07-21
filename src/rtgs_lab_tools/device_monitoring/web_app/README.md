# Device Monitoring Web App

This app displays daily (7 days a week) monitoring checks run by `../scheduled_device_monitoring.sh` on MSI. This app, and the Postgres database with which it interacts, are hosted on Google Cloud. The daily monitoring script pushes its data to this Postgres database.

The website for this app can be found [here](https://device-monitoring-web-711082233215.us-central1.run.app/). You will need to sign in with the lab's credentials.

## Device Status: Problems and Ignores

A device is flagged **Needs Attention** when it has one or more active *problems*. The possible problems mirror the flagging logic in `../data_analyzer.py`:

| Problem key | Meaning |
|---|---|
| `battery` | Battery voltage below the threshold |
| `system` | System power above the threshold |
| `humidity` | Inbox humidity above the threshold |
| `missing` | Node not heard from within the threshold window |
| `error:<NAME>` | A critical error (one problem per critical error present) |

Critical errors are also highlighted (⚠, red) in the dashboard's **Errors** list, matching the daily email.

On each device's page, every active problem has its own **Ignore / Un-ignore** toggle. A device is shown **OK only when every active problem is ignored** (or it has no problems to begin with). For example, a device with a low battery *and* a critical error stays **Needs Attention** until *both* are ignored; if humidity later becomes an issue, the device returns to **Needs Attention** because that new problem has not been ignored.

Ignores are stored in the database (`IgnoredProblem` table), so they are **shared across all users** and **persist until explicitly cleared** — they are not tied to a browser and do not auto-expire when a problem resolves.

## Configuration Tab (Per-Product Overrides)

The **⚙ Configuration** button on the home screen opens an editor for the thresholds and critical-error list. The standard values come from `../config.py` and are shown as **Standard Defaults**. You can override them **per `product_name`** (from the `LoggerInfo` table):

- Editable per product: **battery min voltage**, **system power max**, **inbox humidity max**, and the **critical-error list**.
- Select one, several, or **all** products, choose **Set** (new value) or **Default** (revert) for each field, and **Apply to selected** — a change can be applied to multiple products at once.
- The **Per-Product Configuration** table shows each product's effective values; a `*` marks values overridden from the default. **Reset** clears all overrides for a product.

Overrides affect the **web dashboard only** — the daily monitoring email still uses the standard `config.py` values.

## How Configuration Reaches the Web App

The Cloud Run container is deliberately isolated: the `Dockerfile` packages only `models.py` and `app.py` (plus the built frontend), so **the web app cannot import `config.py`** (it lives outside the build context). Configuration flows through the database instead:

1. The daily pipeline (`produce_db.build_app_config`, called from `core.monitor`) writes the current `config.py` defaults into the `AppConfig` table. This keeps `config.py` as the single source of truth for defaults.
2. The web app serves those defaults at `GET /api/config`, and per-product overrides at `GET /api/product-config` (edited via `PUT /api/product-config`).
3. The **frontend** derives each device's problems from the raw metrics + the effective config (defaults merged with that product's overrides), mirroring `../data_analyzer.py`.

The `IgnoredProblem`, `AppConfig`, and `ProductConfig` tables are created automatically by `db.create_all()` — no manual migration is required. `AppConfig` is populated on the **next pipeline run**; until then the frontend falls back to the defaults baked into `src/utils.js` (`DEFAULT_CONFIG`).

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