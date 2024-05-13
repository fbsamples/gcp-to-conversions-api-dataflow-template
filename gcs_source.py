#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.
import apache_beam as beam

class ReadCSVFromGCS(beam.PTransform):
    
    """
        Reads from a GCS file and formats it to be used by Meta Capi Sink 
        
        Usage: 
            pipeline | 'Read CSV from GCS' >> ReadCSVFromGCS('gs://my-bucket/sample.csv')
    """
    
    # Nested private DoFn 
    class CsvToDictDoFn(beam.DoFn):
    
        def start_bundle(self):
            self.fieldnames = None

        def process(self, element):

            if self.fieldnames is None:
                self.fieldnames = element.split(',')
            else:
                reader = csv.DictReader([element], fieldnames=self.fieldnames)
                row = next(reader)
                row = {k: v for k, v in row.items() if v}
                yield row
    
    def __init__(self, file_path):
        self.file_path = file_path
        
    def expand(self, pcoll):
        return (
            pcoll
            | 'Read the file from GCS' >> beam.io.ReadFromText(self.file_path)
            | 'Convert the CSV into a dictionary for processing' >> beam.ParDo(ReadCSVFromGCS.CsvToDictDoFn())
        )
