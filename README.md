# Google Cloud to Meta Conversions API Dataflow Template

This README provides instructions on how to set up and deploy a Dataflow template that integrates Google Cloud services with Meta's Conversions API.

## Prerequisites
- Google Cloud SDK (gcloud) installed and configured
- Access to Google Cloud Platform (GCP) with necessary permissions

## Setup Instructions

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

### 3. Create a Cloud Storage bucket for storing the template
Create a Cloud Storage bucket to store the Dataflow template:
```
gsutil mb gs://$BUCKET
```

### 4. Create an Artifact Registry repository (if not exists), used for building the template
```
gcloud artifacts repositories create $REPOSITORY \
    --repository-format=docker \
    --location=$REGION
```

### 5. Build the Dataflow template
Build the Dataflow template using the following command
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
