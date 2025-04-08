# Data
The data collection system for the winterturf project consists of:
- Postgres database hosted at MSI for environmental sensing information
- ArcGIS Online for survey data of golf courses
- Google Drive hosted images from UAVs
- Satellite imagery API pulled from Planet Labs

# Data Sources

## Google Drive Data
The primary data for this project is stored in Google Drive at the following location:
https://drive.google.com/drive/folders/1eeRIT-R29MYa_fbE2vwxMjmp2jHh6-4Y?usp=sharing

Use the scripts in the `scripts/data_transfer/` directory to download and process this data.

## GEMS Sensing Database
The GEMS Sensing database is a PostgreSQL database hosted at the Minnesota Supercomputing Institute (MSI) that stores environmental sensor data.

### Connection Details
- **Host**: sensing-0.msi.umn.edu
- **Port**: 5433
- **Database**: gems
- **Access**: Requires UMN credentials with specific permissions

### Database Schema
The database follows an entity-relationship model with these key tables:

1. **node**: Contains information about sensor nodes
   - id (PK): Unique identifier
   - node_id: External identifier for the node
   - display_name: Human-readable name
   - project: Project the node belongs to
   - ownership: Time range of node ownership

2. **node_measure**: Links nodes to their measurement types
   - id (PK): Unique identifier
   - node_id: Reference to node
   - measure: Type of measurement

3. **data**: Contains the actual sensor measurements
   - node_measure_id (FK): Reference to node_measure
   - raw_id (FK): Reference to raw data entry
   - time: Timestamp of measurement
   - value: Measured value

4. **raw**: Contains raw message data from sensors
   - id (PK): Unique identifier
   - node_id: Reference to node
   - publish_time: When data was published
   - ingest_time: When data was ingested
   - event: Event type
   - message: Raw message content
   - message_id: Message identifier

### Access Method
The database is accessed using the `winterturf` view with SQL queries like:
```sql
SELECT * FROM ?.?
WHERE time BETWEEN [start_date] AND [end_date]
```

This view provides filtered access to the sensor data specific to the WinterTurf project.

# Goal
The database should host all of the tabular and vector geospatial data in a single database. The bounding boxes for the imagery data should be stored in the database with reference to a Tier 2 storage bucket on the Minnesota Supercomputing Institute. 

