#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.
"""This module implements IO classes to write data on Meta Conversions API.

Write to Meta Conversions API:
-----------------
:class:`WriteToMetaConversionsAPI` is a ``PTransform`` that writes rows to CAPI.

Example usage::

  pipeline | WriteToMetaConversionsAPI(multi_value_separator="|",
                                      batch_size=25,
                                      access_token=<ACCESS_TOKEN>,
                                      max_api_retry_attempts=3,
                                      api_retry_backoff_factor=2,
                                      api_retry_status_force_list=[500, 502, 503, 504],
                                      metacapisink_timestamp="2024-02-15 18:40:03.796739+00:00") 
                            
"""
import apache_beam as beam
from apache_beam import pvalue
from dataclasses import dataclass
from typing import Iterable
import json
import typing


FAILURES_TAG = 'failures'
OUTPUT_STATUS_FAILURE = 'ERROR'
OUTPUT_STATUS_SUCCESS = 'SUCCESS'

DEFAULT_META_CAPI_ENDPOINT = 'https://graph.facebook.com'
DEFAULT_META_CAPI_API_VERSION = 'v19.0'


@dataclass
class OutputStatusWrapper:
    metacapisink_status: str
    metacapisink_input_element: str
    metacapisink_failure_pipeline_step: str
    metacapisink_output_message: str


class InvalidElementType(TypeError):
    """Error Class for when an Element is not the correct type"""


class _ParseRowToMetaConversionsAPIBody(beam.DoFn):
    """An internal DoFn to be used in a PTransform. Not for external use.
    Parse an element to a Meta Conversions API body
    doc: https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/server-event
    """

    def __init__(self, multi_value_separator: str):
        beam.DoFn.__init__(self)
        self.multi_value_separator = multi_value_separator

    def process(self, element) -> None:
        try:
            # Todo: schema validation
            multi_value_fields = ['em', 'ph', 'ln', 'fn', 'db', 'ge', 'ct', 'st',
                                  'zp', 'country', 'external_id', 'content_ids', 'data_processing_options']
            user_data_fields = ['em', 'ph', 'ln', 'fn', 'db', 'ge', 'ct',
                                'st', 'zp', 'country', 'external_id', 'lead_id', 'madid']
            # make a copy of the original element
            original_element = element.copy()
            # remove all None values and lower case all keys
            element = dict((k.lower(), v)
                           for k, v in element.items() if v is not None)
            # check mandatory fields
            if ('data_set_id' not in element) or ('event_name' not in element) or ('action_source' not in element) or ('event_time' not in element) or (element['event_name'] == 'Purchase' and 'value' not in element) or (element['event_name'] == 'Purchase' and 'currency' not in element):
                raise Exception(
                    'Missing mandatory fields: data_set_id, event_name, action_source, event_time; or currency and value for Purchase events')
            # split multi value columns into array
            for k in multi_value_fields:
                if k in element and element[k] != None:
                    element[k] = element[k].split(self.multi_value_separator)
            # add top level event parameters
            event_data = dict((k, element[k]) for k in ['event_name',
                                                        'event_time',
                                                        'action_source',
                                                        'event_source_url',
                                                        'opt_out',
                                                        'event_id',
                                                        'data_processing_options',
                                                        'data_processing_options_country',
                                                        'data_processing_options_state'] if k in element)
            # init user_data and custom_data
            event_data['user_data'] = {}
            event_data['custom_data'] = {}
            for k, v in element.items():
                # add user_data parameters
                if k in user_data_fields:
                    event_data['user_data'][k] = v
                # add custom_data parameters
                if k not in event_data and k not in user_data_fields and k != 'data_set_id':
                    event_data['custom_data'][k] = v

            # return event data and assign the data_set_id as a Pcollection key
            yield (element['data_set_id'], {'parsed_element': event_data, 'original_element': original_element})

        except Exception as e:
            failure = OutputStatusWrapper(
                metacapisink_status=OUTPUT_STATUS_FAILURE,
                metacapisink_input_element=json.dumps(original_element),
                metacapisink_failure_pipeline_step="_ParseRowToMetaConversionsAPIBody",
                metacapisink_output_message=str(e)
            )
            yield pvalue.TaggedOutput(FAILURES_TAG, failure)


class _MakeMetaConversionsAPICalls(beam.DoFn):
    """An internal DoFn to be used in a PTransform. Not for external use.
    Make an API call using batched elements passed passed as body
    doc: https://developers.facebook.com/docs/marketing-api/conversions-api/using-the-api#send
    """

    def __init__(self, access_token: str, api_retry_total: int, api_retry_backoff_factor: float, api_retry_status_forcelist: list):
        beam.DoFn.__init__(self)
        self.access_token = access_token
        self.api_retry_total = api_retry_total
        self.api_retry_backoff_factor = api_retry_backoff_factor
        self.api_retry_status_forcelist = api_retry_status_forcelist

    # To Do: specify return type for element
    def process(self, element) -> None:
        try:
            if not isinstance(element, Iterable):
                raise InvalidElementType(
                    f"Wrong element type. Expected Iterable[Dict[str, Any]], received {type(element)}")

            # imports need to be here for https requests calls
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            data_set_id = element[0]
            parsed_elements = []
            original_elements = []
            for x in element[1]:
                parsed_elements.append(x['parsed_element'])
                original_elements.append(x['original_element'])

            access_token = self.access_token

            url = f'{DEFAULT_META_CAPI_ENDPOINT}/{DEFAULT_META_CAPI_API_VERSION}/{data_set_id}/events?access_token={access_token}'

            retry = Retry(total=self.api_retry_total, backoff_factor=self.api_retry_backoff_factor,
                          status_forcelist=self.api_retry_status_forcelist)
            adapter = HTTPAdapter(max_retries=retry)
            _session = requests.Session()
            _session.mount('https://', adapter)

            req_body = {"data": parsed_elements}

            response = _session.post(url, json=req_body)
            ok = response.status_code < 400
            if not ok:
                failure = OutputStatusWrapper(
                    metacapisink_status=OUTPUT_STATUS_FAILURE,
                    metacapisink_input_element=original_elements,
                    metacapisink_failure_pipeline_step="_MakeMetaConversionsAPICalls",
                    metacapisink_output_message=json.dumps(response.json())
                )
                yield pvalue.TaggedOutput(FAILURES_TAG, failure)
            if ok:
                yield json.dumps(response.json()), original_elements
        except Exception as e:
            raise e


class WriteToMetaConversionsAPI(beam.PTransform):
    def __init__(self,
                 multi_value_separator: str,
                 batch_size: int,
                 access_token: str,
                 max_api_retry_attempts: int,
                 api_retry_backoff_factor: float,
                 api_retry_status_force_list: [int],
                 metacapisink_timestamp: str,
                 **kwargs):

        beam.PTransform.__init__(self)
        self.multi_value_separator = multi_value_separator
        self.batch_size = batch_size
        self.access_token = access_token
        self.max_api_retry_attempts = max_api_retry_attempts
        self.api_retry_backoff_factor = api_retry_backoff_factor
        self.api_retry_status_force_list = api_retry_status_force_list
        self.metacapisink_timestamp = metacapisink_timestamp
        self.kwargs = kwargs

    def expand(self, pcoll):

        # First step: convert the input rows to conversions api body
        _step_parse_to_capi_format = pcoll | beam.ParDo(_ParseRowToMetaConversionsAPIBody(
            self.multi_value_separator)).with_outputs(FAILURES_TAG, main='outputs')
        # Second step: for all successuful rows (no parsing errors), group into micro batches and make bulk api calls to meta
        _step_make_capi_calls = (
            _step_parse_to_capi_format['outputs']
            | beam.GroupIntoBatches(self.batch_size)
            | beam.ParDo(_MakeMetaConversionsAPICalls(access_token=self.access_token,
                                                      api_retry_total=self.max_api_retry_attempts,
                                                      api_retry_backoff_factor=self.api_retry_backoff_factor,
                                                      api_retry_status_forcelist=self.api_retry_status_force_list)
                         ).with_outputs(FAILURES_TAG, main='outputs'))

        # _step_make_capi_calls if successful, returns a tuple of (capi api response, list of rows included on the bulk api), split those rows
        _collect_successful_output = (
            _step_make_capi_calls['outputs']
            | 'SplitSuccessOutputs' >> beam.FlatMap(lambda elt: [OutputStatusWrapper(metacapisink_status=OUTPUT_STATUS_SUCCESS,
                                                                                     metacapisink_input_element=i,
                                                                                     metacapisink_failure_pipeline_step=None,
                                                                                     metacapisink_output_message=elt[0])
                                                                 for i in elt[1]])
        )
        # _step_parse_to_capi_format if failure, returns OutputStatusWrapper object with individual failed row
        _collect_failure_step_parse_to_capi_format = _step_parse_to_capi_format['failures']
        # _step_make_capi_calls if failure, returns OutputStatusWrapper object with list of rows failed
        # (in case of issue with one row, capi rejects all rows included on the bulk api, split those row
        _collect_failure_step_make_capi_calls = (
            _step_make_capi_calls['failures']
            | 'SplitFailureOutputs' >> beam.FlatMap(lambda elt: [OutputStatusWrapper(metacapisink_status=OUTPUT_STATUS_FAILURE,
                                                                                     metacapisink_input_element=i,
                                                                                     metacapisink_failure_pipeline_step=elt.metacapisink_failure_pipeline_step,
                                                                                     metacapisink_output_message=elt.metacapisink_output_message)
                                                                 for i in elt.metacapisink_input_element]))

        # collect final output and all failures
        _collect_all_outputs = ((_collect_successful_output, _collect_failure_step_parse_to_capi_format, _collect_failure_step_make_capi_calls)
                                | beam.Flatten()
                                | 'ConvertToBigQueryDict' >> beam.Map(lambda elt: {'metacapisink_timestamp': self.metacapisink_timestamp,
                                                                                   'metacapisink_status': elt.metacapisink_status,
                                                                                   'metacapisink_failure_pipeline_step': elt.metacapisink_failure_pipeline_step,
                                                                                   'metacapisink_output_message': elt.metacapisink_output_message,
                                                                                   'metacapisink_input_element': str(elt.metacapisink_input_element)})
                                )

        return _collect_all_outputs
