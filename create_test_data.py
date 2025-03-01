#!/usr/bin/env python
"""Script to create test data for BLIMS."""

from test_data import create_test_data
from blims.core.service import SampleService

if __name__ == "__main__":
    service = SampleService()
    create_test_data(service)
    print("Test data creation complete.")