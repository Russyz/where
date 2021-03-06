#!/usr/bin/env python3
"""Write Where dataset fields by selecting the used "writers"

Usage::

    {exe:tools} write <date> <pipeline> --stage=<stage> --writers=<writers> [options]

The program requires a date. Typically, the date is given in the format
`<year month day>` (for example 2015 8 4). However, it is also possible to
specify the date as `<year day-of-year>` (for example 2015 216) by also adding
the option `--doy`.

The following commands are required:

===================  ===========================================================
Command              Description
===================  ===========================================================
date                 The starting date in the format ``<year month day>``.
{pipelines_doc:Write results from}
--stage=             Stage of analysis.
--writers=           List with writers.
===================  ===========================================================

Furthermore, the following options are recognized:

===================  ===========================================================
Option               Description
===================  ===========================================================
--doy                Specify date as <year day-of-year>.
--dset_id=           Dataset identifier (Default: 'last').
--id=                Analysis identifier (Default: '').
--session=           Session name (Default: '').
-h, --help           Show this help message and exit.
===================  ===========================================================

Description:
------------

Read Where dataset and write Where datasets fields via a defined writer.

Example:
--------

  {exe:tools} write 2018 10 26 --sisre --stage=calculate --dset_id=1 --id='grc_inav_e1_std_sat' --writers=sisre_plot
  {exe:tools} write 2019 2 1 --gnss --session=stas --stage=estimate --dset_id=last --writers=gnss_report
"""
# Midgard imports
from midgard.dev import plugins
from midgard.writers import write as write_

# Where imports
from where.lib import config
from where import data
from where.lib import log
from where.lib import util


@plugins.register
def write(rundate: "datedoy", tech: "pipeline", stage: "option", writers: "option"):
    log.init(log_level="info")

    # Get options
    writer_names = writers.replace(",", " ").split()
    dataset_id = util.read_option_value("--dset_id", default="last")
    dataset_id = "last" if dataset_id == "last" else int(dataset_id)
    identifier = util.read_option_value("--id", default="")
    identifier = f"-{identifier}" if identifier else ""
    session = util.read_option_value("--session", default="")

    dset = data.Dataset(
        rundate=rundate, tech=tech, stage=stage, id=identifier, dataset_name=session, dataset_id=dataset_id
    )

    path_hdf5 = config.files.path("dataset_hdf5", file_vars=dset.vars)
    path_json = config.files.path("dataset_json", file_vars=dset.vars)
    log.info(f"Read Where dataset files {path_hdf5} and {path_json}.")

    if dset.num_obs == 0:
        log.fatal(f"No data to read for date {rundate}.")

    # Loop over writers
    for writer in writer_names:
        log.info(f"Apply writer '{writer}'.")
        write_(writer, dset=dset)
