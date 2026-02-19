"""
Hierarchical Classification of Cancer Cell Lineages via Proteomic Maps
Author: Nuru Khaliel 
Description: This script implements a two-stage Random Forest classifier to 
predict tissue identity from high-dimensional proteomic data.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler
from umap import UMAP

# Setup professional logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def load_and_preprocess():
    """Load metadata and protein matrix from supplemental files."""
    logging.info("Loading and merging data...")
    # Update paths to match your repo structure
    try:
        meta_df = pd.read_excel("data/mmc2.xlsx", sheet_name="Cell line level sample info", header=1)
        data_df = pd.read_excel("data/mmc3.xlsx", header=1)
    except FileNotFoundError:
        logging.error("Data files not found in /data folder. Please download supplemental tables.")
        return None, None

    # Data cleaning and merging logic from original script
    data_df.rename(columns={data_df.columns[0]: "Project_Identifier"}, inplace=True)
    data_df["model_id_clean"] = data_df["Project_Identifier"].apply(lambda x: str(x).split(";")[0])
    
    combined_df = pd.merge(
        meta_df[["model_id", "Tissue_type"]],
        data_df,
        left_on="model_id",
        right_on="model_id_clean",
        how="inner"
    )
    
    # Filter N >= 50 and feature selection (10% threshold)
    tissue_counts = combined_df["Tissue_type"].value_counts()
    valid_tissues = tissue_counts[tissue_counts >= 50].index
    filtered_df = combined_df[combined_df["Tissue_type"].isin(valid_tissues)].copy()
    
    protein_columns = [col for col in filtered_df.columns if ";" in str(col)]
    filtered_df[protein_columns] = filtered_df[protein_columns].fillna(0)
    
    min_samples = len(filtered_df) * 0.10
    selected_proteins = filtered_df[protein_columns].astype(bool).sum(axis=0)
    selected_proteins = selected_proteins[selected_proteins > min_samples].index.tolist()
    
    return filtered_df, selected_proteins

def run_models(df, features):
    """Execute hierarchical classification: Lineage then Subtype."""
    logging.info("Training hierarchical models...")
    
    # Model 1: Lineage (Haematopoietic vs Solid)
    df["Lineage"] = df["Tissue_type"].apply(lambda t: "Haematopoietic" if t == "Haematopoietic and Lymphoid" else "Solid")
    X = df[features]
    y_lineage = df["Lineage"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y_lineage, test_size=0.3, stratify=y_lineage, random_state=42)
    rf_lin = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)
    rf_lin.fit(X_train, y_train)
    
    logging.info(f"Model 1 (Lineage) Accuracy: {rf_lin.score(X_test, y_test):.2%}")
    
    # Model 2: Subtype (Solid tissues only)
    solid_df = df[df["Lineage"] == "Solid"].copy()
    X_solid = solid_df[features]
    y_subtype = solid_df["Tissue_type"]
    
    # Stratified 5-fold CV for Model 2
    rf_sub = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(rf_sub, X_solid, y_subtype, cv=cv)
    
    logging.info(f"Model 2 (Subtype) CV Mean Accuracy: {scores.mean():.2%}")

if __name__ == "__main__":
    df, features = load_and_preprocess()
    if df is not None:
        run_models(df, features)
