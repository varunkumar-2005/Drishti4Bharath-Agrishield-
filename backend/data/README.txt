Place your files here:
- trade_dataset.csv     (your 139,626 row India bilateral trade dataset)
- risk_model.pkl        (XGBoost model — run train_model.py to generate)
- encoders.pkl          (LabelEncoder for risk classes)
- feature_columns.pkl   (list of feature column names)

Then upload to S3: python setup_s3.py
