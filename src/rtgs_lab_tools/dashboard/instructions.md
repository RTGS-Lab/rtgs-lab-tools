- `Project-Shoco` repo: copy the `dashboard` directory into the `rtgs-lab-tools/src/rtgs_lab_tools` directory.
- From the `feature/nick-data-analysis` branch of the `Project-Shoco` repo, copy the `scripts` subdirectory from the `winterturf_analysis` directory and paste into `rtgs-lab-tools/src/rtgs_lab_tools/dashboard`
- Inside the `dashboard` directory, create a `.env` file and fill it out with the database credentials (same as the credentials for the overall `rtgs-lab-tools` repo).

~~~
	DB_HOST=
	DB_PORT=
	DB_NAME=
	DB_USER=
	DB_PASSWORD=
~~~

## How to Run
- The `streamlit` package needs to be installed.
- From the `dashboard` directory inside the `rtgs-lab-tools` repo, use the command `uv run streamlit run dashboard.py` to run the dashboard.
- Alternatively, you can also use `python -m streamlit run dashboard.py` to run the dashboard without `uv`.
- The dashboard will take a little time to load but should then open up automatically in your browser. Once it does that, the screen will be blank for a little bit while the dashboard loads. Be patient.