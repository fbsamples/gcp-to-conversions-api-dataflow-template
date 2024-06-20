#!/usr/bin/env python

#  Google Cloud to Meta Conversions API Dataflow connector
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from custom_sink import conversions_api_io, gcs_source
from datetime import timezone
import datetime

class MetaCAPIConnectorOptions(PipelineOptions):
    
    @classmethod
    def _add_argparse_args(cls, parser):
        parser.add_argument("--inputFileSpec", help="Path to the input CSV file in GCS")
        parser.add_argument("--multi_value_separator",
                            default="|",
                            type=str,
                            required=False)
        parser.add_argument('--access_token', type=str)
        parser.add_argument('--batch_size', type=int, required=False)
        parser.add_argument('--max_api_retry_attempts',
                            type=int, required=False)
        parser.add_argument('--api_retry_backoff_factor',
                            type=float, required=False)
        parser.add_argument("--outputTableSpec")
        parser.add_argument("--output_type", type=str)
                            
                                                
options = MetaCAPIConnectorOptions()

with beam.Pipeline(options=options) as pipeline:

    process_start_timestamp = datetime.datetime.now(timezone.utc)

    def output_status_filter(elt, output_type):
        if 'metacapisink_status' not in elt:
            return False

        if output_type == 'ERROR_ONLY':
            return elt['metacapisink_status'] == 'ERROR'
        elif output_type == 'SUCCESS_ONLY':
            return elt['metacapisink_status'] == 'SUCCESS'
        else:
            return True

    # read from GCS and write on Conversions API
    gcstocapi = (
        pipeline
        | 'Read from GCS' >> gcs_source.ReadCSVFromGCS(options.inputFileSpec)
        | 'Write to Meta CAPI' >> conversions_api_io.WriteToMetaConversionsAPI(multi_value_separator=options.multi_value_separator,
                                                                               batch_size=options.batch_size,
                                                                               access_token=options.access_token,
                                                                               max_api_retry_attempts=options.max_api_retry_attempts,
                                                                               api_retry_backoff_factor=options.api_retry_backoff_factor,
                                                                               api_retry_status_force_list=[
                                                                                   500, 502, 503, 504],
                                                                               metacapisink_timestamp=process_start_timestamp
                                                                               )
    )
    # Write CAPI output to Dead Letter Queue
    (gcstocapi
     | 'Filter CAPI output' >> beam.Filter(output_status_filter, options.output_type)
     | 'Write output to DLQ' >> beam.io.WriteToBigQuery(options.outputTableSpec,
                                                        schema='metacapisink_timestamp:STRING,metacapisink_status:STRING, metacapisink_failure_pipeline_step:STRING, metacapisink_output_message:STRING, metacapisink_input_element:STRING',
                                                        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                                                        create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED))
