## Enable APIs
```
gcloud services enable dataflow compute_component logging storage_component storage_api cloudresourcemanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

## Set variable for your GCP project
```
export BUCKET="YOUR_TEMPLATE_LOCATION_BUCKET"
export REGION="YOUR_GCP_REGION"
export REPOSITORY="YOUR_GCP_CONTAINER_REPOSITORY"
export PROJECT="YOUR_GCP_PROJECT"
gcloud config set project $PROJECT
```

## Create a Cloud Storage bucket for storing the template
```
gsutil mb gs://$BUCKET
```

## Create an Artifact Registry repository (if not exists), used for building the template
```
gcloud artifacts repositories create $REPOSITORY \
    --repository-format=docker \
    --location=$REGION
```

## Build the Dataflow template
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
## License
gcp-to-conversions-api-dataflow is MIT licensed, as found in the LICENSE file.
