# Data Preprocessing

This folder contains the notebooks used to collect, inspect, and prepare mosquito audio data for model training.

The preprocessing workflow focuses on three main tasks:

1. Pulling datasets from Zenodo and Kaggle.
2. Uploading or mirroring prepared datasets to Hugging Face for easier reuse and sharing.
3. Running exploratory data analysis to understand the dataset structure, label distribution, and class imbalance.

## What is in this folder

- `data_preprocessing_1.ipynb` - raw audio preprocessing for the HumBugDB dataset, including download, extraction, filtering, waveform processing, and PyTorch dataset creation.
- `DataPreprocessingandEDAhumbug.ipynb` - preprocessing and exploratory analysis for the HumBugDB data.
- `DataPreprocessingandEDAkaggle.ipynb` - preprocessing and exploratory analysis for the Kaggle-sourced data.
- `Kaggle_to_HF.ipynb` - uploads the Kaggle-prepared dataset to Hugging Face.
- `Zenodo_to_HF.ipynb` - uploads the Zenodo-prepared dataset to Hugging Face.

## Typical Workflow

The notebooks in this folder generally follow this sequence:

1. Download the source data from Zenodo or Kaggle.
2. Clean and organize the audio files and metadata.
3. Run EDA to check counts, class balance, and other basic dataset properties.
4. Export the prepared data or publish it to Hugging Face for later model training.

## EDA Goals

The exploratory analysis in this folder is mainly used to:

- Inspect how many samples are available for each mosquito class.
- Check whether the dataset is imbalanced across species or labels.
- Spot missing files, unexpected metadata values, or other data quality issues early.

## Outputs

Depending on the notebook, outputs may include:

- downloaded raw archives or metadata files
- extracted `.wav` audio files
- cleaned metadata tables
- processed tensors or dataset shards
- uploaded dataset artifacts on Hugging Face

## Notes

- This folder is focused on preprocessing and analysis only.
- Model training code lives in the training folder under `model_training`.
