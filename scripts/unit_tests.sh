#!/bin/sh

python db/wait_for_db.py
pytest tests/unit
python tests/drop_test_data.py