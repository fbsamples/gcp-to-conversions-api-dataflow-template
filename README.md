# Google Cloud to Meta Conversions API Dataflow Template

This README provides instructions on how to setup and use a Dataflow template that integrates Google Cloud services with Meta's Conversions API.

## About the Google Cloud to Meta CAPI Dataflow template
The GCP to Meta CAPI template encapsulates the logic for reading data from a Google Cloud source (BigQuery or Google Cloud Storage) and sending that data to Meta using Conversions API. It was developed for events collected in batch (like Offline events) and is not suitable for real-time events. Below are the data processing steps managed by the template and the Meta CAPI connector:
- (1) Read offline events from a BigQuery table or Google Cloud Storage file;
- (2) Parse single record to the Conversions API Json;
- (3) Group the parsed records into micro-batches (e.g. 50 events per API call);
- (4) Make the API calls to Conversions API and store the output logs (success or failure) into a dead letter table defined by the advertiser.

![Alt text](gcp_to_capi_dataflow_logic.png?raw=true "Processing logic")


## How to install

###  Prerequisites
- Google Cloud SDK (gcloud) installed and configured;
- Access to Google Cloud Platform (GCP) with necessary permissions.

### 1. Enable Required APIs
Enable the necessary APIs by running the following command:

```
gcloud services enable dataflow compute_component logging storage_component storage_api cloudresourcemanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```
### 2. Configure GCP environment variables
Set the environment variables for your GCP project:
```
export BUCKET="YOUR_TEMPLATE_LOCATION_BUCKET"
export REGION="YOUR_GCP_REGION"
export REPOSITORY="YOUR_GCP_CONTAINER_REPOSITORY"
export PROJECT="YOUR_GCP_PROJECT"
gcloud config set project $PROJECT
```

### 3. Create a Cloud Storage bucket for storing the templates
Create a Cloud Storage bucket to store the Dataflow template:
```
gsutil mb gs://$BUCKET
```

### 4. Create an Artifact Registry repository (if not exists), used for building the templates
```
gcloud artifacts repositories create $REPOSITORY \
    --repository-format=docker \
    --location=$REGION
```

### 5. Build the Dataflow template

#### 5.1 Install the Dataflow template for BigQuery to Meta Conversions API
Build the Dataflow template using the command below. The resulting template file will be stored on the bucket defined above.
```
export TEMPLATE_NAME="bigquery_to_meta_conversions_api"
gcloud dataflow flex-template build gs://$BUCKET/$TEMPLATE_NAME.json \
    --image-gcr-path "$REGION-docker.pkg.dev/$PROJECT/$REPOSITORY/$TEMPLATE_NAME:latest" \
    --sdk-language "PYTHON" \
    --flex-template-base-image "PYTHON3" \
    --py-path "." \
    --metadata-file "${TEMPLATE_NAME}_metadata.json" \
    --env "FLEX_TEMPLATE_PYTHON_PY_FILE=$TEMPLATE_NAME.py" \
    --env "FLEX_TEMPLATE_PYTHON_REQUIREMENTS_FILE=requirements.txt"\
    --env "FLEX_TEMPLATE_PYTHON_SETUP_FILE=setup.py"
```

#### 5.2 Install the Dataflow template for Google Cloud Storage (GCS) to Meta Conversions API
Build the Dataflow template using the command below. The resulting template file will be stored on the bucket defined above.
```
export TEMPLATE_NAME="gcs_to_meta_conversions_api"
gcloud dataflow flex-template build gs://$BUCKET/$TEMPLATE_NAME.json \
    --image-gcr-path "$REGION-docker.pkg.dev/$PROJECT/$REPOSITORY/$TEMPLATE_NAME:latest" \
    --sdk-language "PYTHON" \
    --flex-template-base-image "PYTHON3" \
    --py-path "." \
    --metadata-file "${TEMPLATE_NAME}_metadata.json" \
    --env "FLEX_TEMPLATE_PYTHON_PY_FILE=$TEMPLATE_NAME.py" \
    --env "FLEX_TEMPLATE_PYTHON_REQUIREMENTS_FILE=requirements.txt"\
    --env "FLEX_TEMPLATE_PYTHON_SETUP_FILE=setup.py"
```

## How to use

###  Prerequisites
- Access to Google Cloud Platform (GCP) with necessary permissions.
- Meta Conversions API access token (https://developers.facebook.com/docs/marketing-api/conversions-api/get-started/). If you serve multiple datasets from the same table, you should generate a system user access token rather than a dataset-scoped access token.
  
### 1. Expected source format (for both BigQuery and GCS)

Below is the expected table source format, please consult following documentation for further details:
- Standard parameters: https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/server-event/
- Custom data fields: https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/custom-data 
- User data fields (hashing and normalization requirements): https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/customer-information-parameters 

| Field name    | Type | Mandatory | Multi-value| Description |
| -------- | ------- | ------- | ------- | ------- |
| data_set_id  | INTEGER    | Yes  | No    | Destination data_set_id (e.g. 350218134519384)  |
| event_name  | STRING    | Yes  | No    | Event name (e.g. Purchase)  |
| event_time  | INTEGER    | Yes  | No    | Unix timestamp in seconds indicating when the actual event occurred (eg. 1708211706)  |
| action_source  | STRING    | Yes  | No    | Should be “physical_store” for Offline events  |
| order_id  | STRING    | No  | No    | Unique transaction or order ID (e.g. order1234)  |
| value  | FLOAT    | Yes if event_name = ‘Purchase’ | No    | Value of the purchase (e.g. 150.5). Optional for non-Purchase event  |
| currency  | INTEGER    | Yes if event_name = ‘Purchase’  | No    | Currency (e.g. GBP),  must be a valid ISO 4217 three-digit currency code. Optional for non-Purchase event  |
| content_ids  | STRING    | No | Yes    | Multiple value, Content IDs/SKU associated with the events. For multiple values, use a separator (e.g. ABC\|EFG)  |
| em  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| ph  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| ln  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| fn  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| db  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| ct  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| zp  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| st  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| country  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| external_id  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| madid  | STRING    | No | No    | Mobile advertiser ID |90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| ge  | STRING    | No | Yes    | Multiple value, Hashed and normalized email. For multiple values, use a separator (e.g. 62a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f62f\|90a14e44f765419d10fea99367361a727c12365e2520f32218d505ed9aa0f33f) |
| content_type  | STRING    | No | No    | Should be either “product” or “product_group” depending on the type of contents send on the “content_ids” |
| num_items  | INTEGER    | No | No    | Use only with InitiateCheckout events. The number of items that a user tries to buy during checkout. |
| custom_prop*  | STRING | No | No    | Any non-standard parameters added by the advertisers |

### 2. Dataflow template parameters

| Parameter | Type | Required | Default value | Description |
| -------- | ------- | ------- | ------- | ------- |
| BigQuery Source Table  | GCP Table ID | Yes | - | Source table, should be a GCP table ID (bigquery-project:dataset.input_table) |
| Conversions API access token  | STRING | Yes | - | Access Token for accessing Conversions API. Check instructions here: https://developers.facebook.com/docs/marketing-api/conversions-api/get-started/#access-token |
| BigQuery Dead Letter Queue table  | GCP Table ID | Yes | - | Source table, should be a GCP table ID (bigquery-project:dataset.input_table) |
| BigQuery Source Table | GCP Table ID | Yes | - | Table where to store API outputs(success or/and error message and input), should be a GCP table ID (bigquery-project:dataset.output_table) |
| BigQuery Dead Letter Queue filter output | ENUN: (ERROR_ONLY, SUCCESS_ONLY, ALL) | Yes | - | Type of output to logs: ERROR_ONLY: only logs output with errors; SUCCESS_ONLY: only output with success API response; ALL: logs all output including errors and success |
| Multi value separator | STRING | No | \| | Separator used for fields having multiple values such as emails (em), phones(ph) or content IDs (content_ids) |
| Batch Size (number max of events per conversions api call) | INT | No | 50 | Number max of rows per single API call. Default value 50 |
| Max Conversions API retry attempts | INT | No | 3 | Number max of retry in case of server error. Default 3 |
| Exponential backoff factor for Conversions API retry | FLOAT | No | 2 | Number of times to wait in case of server error. Default, use an exponential factor of 2 |


## Pipeline Code Overview

The Python script provided is a Dataflow pipeline that reads data from a BigQuery table, processes it, and writes the results to Meta's Conversions API. It also supports writing failed records to a Dead Letter Queue in BigQuery.

### Key Components:
- *MetaCAPIConnectorOptions*: Custom options for the pipeline.
- *Read from BigQuery*: Reads data from the specified BigQuery table.
- *Write to Meta CAPI*: Custom I/O transform to write data to Meta's Conversions API.
- *Filter CAPI output*: Filters the output based on the status (e.g., ERROR_ONLY).
- *Write output to DLQ*: Writes failed records to a specified BigQuery table.





## License
gcp-to-conversions-api-dataflow is MIT licensed, as found in the LICENSE file.
