#!/usr/bin/env python
# coding: utf-8

# # Single-cell Profiling Walkthrough
#
# Welcome to this walkthrough where we will guide you through the process of extracting single cell morphology features using the [pycytominer](https://github.com/cytomining/pycytominer) API.
#
# For this walkthrough, we will be working with the NF1-Schwann cell morphology dataset.
# If you would like the more information about this dataset, you can refer to this [repository](https://github.com/WayScience/nf1_cellpainting_data)
#
# From the mentioned repo, we specifically used this [dataset](https://github.com/WayScience/nf1_cellpainting_data/tree/main/2.cellprofiler_analysis/analysis_output) and the associated [metadata](https://github.com/WayScience/nf1_cellpainting_data/tree/main/0.download_data/metadata) to generate the walkthrough.
#
#
# Let's get started with the walkthrough below!

# In[1]:


import pathlib

import pandas as pd

# pycytominer imports
from pycytominer.cyto_utils.cells import SingleCells
from pycytominer import annotate, normalize, feature_select

# ignore mix type warnings from pandas
import warnings

warnings.filterwarnings("ignore")


# ## About the inputs
#
#
# In this section, we will set up the expected input and output paths that will be generated throughout this walkthrough. Let's take a look at the explanation of these inputs and outputs.
#
# For this workflow, we have two main inputs:
#
# - **plate_data** (SQLite file): This contains the quantified single-cell morphology features that we'll be working with.
# - **plate_map** (CSV file): This contains additional information related to the cells, providing valuable context of our single-cell morphology dataset.
#
# Now, let's explore the outputs generated in this workflow. In this walkthrough, we will be generating four profiles:
#
# - **sc_profiles_path**: This refers to the single-cell morphology profile that will be generated.
# - **anno_profiles_path**: This corresponds to the annotated single-cell morphology profile, meaning the information from the **plate_map** is added to each single-cell
# - **norm_profiles_path**: This represents the normalized single-cell morphology profile.
# - **feat_profiles_path**: Lastly, this refers to the selected features from the single-cell morphology profile.
#
# **Note**: All profiles are outputted as `.csv` files, however, users can output these files as `parquet` or other file file formats.
# For more information about output formats, please refer the documentation [here](https://pycytominer.readthedocs.io/en/latest/pycytominer.cyto_utils.html#pycytominer.cyto_utils.output.output)
#
# These profiles will serve as important outputs that will help us analyze and interpret the single-cell morphology data effectively. Now that we have a clear understanding of the inputs and outputs, let's proceed further in our walkthrough.

# In[2]:


# Setting file paths
data_dir = pathlib.Path("./data/").resolve(strict=True)
metadata_dir = (data_dir / "metadata").resolve(strict=True)
out_dir = pathlib.Path("results")
out_dir.mkdir(exist_ok=True)

# input file paths
plate_data = pathlib.Path("./data/nf1_data.sqlite").resolve(strict=True)
plate_map = (metadata_dir / "platemap_NF1_CP.csv").resolve(strict=True)

# setting output paths
sc_profiles_path = out_dir / "nf1_single_cell_profile.csv.gz"
anno_profiles_path = out_dir / "nf1_annotated_profile.csv.gz"
norm_profiles_path = out_dir / "nf1_normalized_profile.csv.gz"
feat_profiles_path = out_dir / "nf1_features_profile.csv.gz"


# ## Generating Merged Single-cell Morphology Dataset
#
# In this section of the walkthrough, our goal is to load the NF1 dataset and create a merged single-cell morphology dataset.
#
# Currently, the NF1 morphology `SQLite` dataset was generated by using [CellProfiler's](https://github.com/CellProfiler/CellProfiler) [ExportToDatabase](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.5/modules/fileprocessing.html?highlight=exporttodatabase#module-cellprofiler.modules.exporttodatabase) function, where each table represents a different compartment, such as Image, Cell, Nucleus, and Cytoplasm.
#
# To achieve this, we will utilize the SingleCells class, which offers a range of functionalities specifically designed for single-cell analysis. You can find detailed documentation on these functionalities [here](https://pycytominer.readthedocs.io/en/latest/pycytominer.cyto_utils.html#pycytominer.cyto_utils.cells.SingleCells).
#
# However, for our purpose in this walkthrough, we will focus on using the SingleCells class to merge all the tables within the NF1 sqlite file into a merged single-cell morphology dataset.
#
# ### Updating defaults
# Before we proceed further, it is important to update the default parameters in the `SingleCells`class to accommodate the table name changes in our NF1 dataset.
#
# Since the table names in our NF1 dataset differ from the default table names recognized by the `SingleCells` class, we need to make adjustments to ensure proper recognition of these table name changes.

# In[3]:


# update compartment names and strata
strata = ["Image_Metadata_Well", "Image_Metadata_Plate"]
compartments = ["Per_Cells", "Per_Cytoplasm", "Per_Nuclei"]

# Updating linking columns for merging all compartments
linking_cols = {
    "Per_Cytoplasm": {
        "Per_Cells": "Cytoplasm_Parent_Cells",
        "Per_Nuclei": "Cytoplasm_Parent_Nuclei",
    },
    "Per_Cells": {"Per_Cytoplasm": "Cells_Number_Object_Number"},
    "Per_Nuclei": {"Per_Cytoplasm": "Nuclei_Number_Object_Number"},
}


# Now that we have stored the updated parameters, we can use them as inputs for `SingleCells` class to merge all the NF1 sqlite tables into a single consolidated dataset.
#
# This is done through the `merge_single_cells` method. For more infromation about `merge_single_cells` please refer to the documentation [here](https://pycytominer.readthedocs.io/en/latest/pycytominer.cyto_utils.html#pycytominer.cyto_utils.cells.SingleCells.merge_single_cells)

# In[4]:


# setting up sqlite address
sqlite_address = f"sqlite:///{str(plate_data)}"

# loading single cell morphology data into pycyotminer's SingleCells Object
single_cell_profile = SingleCells(
    sql_file=sqlite_address,
    compartments=compartments,
    compartment_linking_cols=linking_cols,
    image_table_name="Per_Image",
    strata=strata,
    merge_cols=["ImageNumber"],
    image_cols="ImageNumber",
    load_image_data=True,
)

# merging all sqlite table into a single tabular dataset (csv) and save as
# compressed csv file
single_cell_profile.merge_single_cells(
    sc_output_file=sc_profiles_path, compression_options="gzip"
)


# Now that we have created our merged single-cell profile, let's move on to the next step: loading our `platemaps`.
#
# Platemaps provide us with additional information that is crucial for our analysis. They contain details such as well positions, genotypes, gene names, perturbation types, and more. In other words, platemaps serve as a valuable source of metadata for our single-cell morphology profile.
#

# In[5]:


# loading plate map and display it
platemap_df = pd.read_csv(plate_map)

# displaying platemap
print(platemap_df.columns.tolist())


# ## Annotation
#
# In this step of the walkthrough, we will combine the metadata with the merged single-cell morphology dataset. To accomplish this, we will utilize the `annotation` function provided by `pycytominer`.
#
# The `annotation` function takes two inputs: the merged single-cell morphology dataset and its associated plate map. By combining these two datasets, we will generate an annotated_profile that contains enriched information.
#
# More information about the `annotation` function can be found [here](https://pycytominer.readthedocs.io/en/latest/pycytominer.html#module-pycytominer.annotate)
#

# In[6]:


# annotating merged single-cell profile with metadata
annotate(
    profiles=sc_profiles_path,
    platemap=platemap_df,
    join_on=["Metadata_well_position", "Image_Metadata_Well"],
    output_file=anno_profiles_path,
    compression_options="gzip",
)

# save message display
print(f"Annotated profile saved in: {anno_profiles_path}")


# ## Normalization Step
#
# The next step is to normalize our dataset using the `normalize` function provided by `pycytominer`.
# More information regards `pycytominer`'s `normalize` function can be found [here](https://pycytominer.readthedocs.io/en/latest/pycytominer.html#module-pycytominer.normalize)
#
# Normalization is a critical preprocessing step that improves the quality of our dataset. It addresses two key challenges: mitigating the impact of outliers and handling variations in value scales. By normalizing the data, we ensure that our downstream analysis is not heavily influenced by these factors.
#
# Additionally, normalization plays a crucial role in determining feature importance (which is crucial for our last step). By bringing all features to a comparable scale, it enables the identification of important features without biases caused by outliers or widely-scaled values.
#
# To normalize our annotated single-cell morphology profile, we will utilize the `normalize` function from `pycytominer`. This function is specifically designed to handle the normalization process for cytometry data.

# In[7]:


# normalize dataset
normalize(
    profiles=anno_profiles_path,
    features="infer",
    image_features=False,
    meta_features="infer",
    samples="all",
    method="standardize",
    output_file=norm_profiles_path,
    compression_options="gzip",
)

# save message display
print(f"Normalized profile saved in: {norm_profiles_path}")


# ## Feature Selection
#
#
# In the final section of our walkthrough, we will utilize the normalized dataset to extract important morphological features and generate a selected features profile.
#
# To accomplish this, we will make use of the `feature_select` function provided by `pycytominer`.
# Using `pycytominer`'s `feature_select` function to our dataset, we can identify the most informative morphological features that contribute significantly to the variations observed in our data. These selected features will be utilized to create our feature profile.
#
# For more detailed information about the `feature_select` function, its parameters, and its capabilities, please refer to the documentation available [here](https://pycytominer.readthedocs.io/en/latest/pycytominer.html#module-pycytominer.feature_select).
#

# In[8]:


# creating selected features profile
feature_select(
    profiles=norm_profiles_path,
    features="infer",
    image_features=False,
    samples="all",
    operation=["variance_threshold", "correlation_threshold", "blocklist"],
    output_file=feat_profiles_path,
    compression_options="gzip",
)

# save message display
print(f"Selected features profile saved in: {feat_profiles_path}")


# Congratulations! You have successfully completed our walkthrough. We hope that it has provided you with a basic understanding of how to analyze cell morphology features using `pycytominer`.
#
# By following the steps outlined in this walkthrough, you have gained valuable insights into processing high-dimensional single-cell morphology data with ease using `pycytominer`. However, please keep in mind that `pycytominer` offers a wide range of functionalities beyond what we covered here. We encourage you to explore the documentation to discover more advanced features and techniques.
#
# If you have any questions or need further assistance, don't hesitate to visit the `pycytominer` repository and post your question in the [issues](https://github.com/cytomining/pycytominer/issues) section. The community is there to support you and provide guidance.
#
# Now that you have the knowledge and tools to analyze cell morphology features, have fun exploring and mining your data!