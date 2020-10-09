# -*- coding: utf-8 -*-
# 
# Convert conda-environment YAML file to pip-style requirements.txt
#

# Builtin/3rd party package imports
import ruamel.yaml
import datetime
import os

# List of keywords to search for in comments highlighting optional packages
commentKeys = ["test", "optional", "development"]

# Map conda packages to their respective pip equivalents
pkgConvert = {"python-graphviz" : "graphviz"}


def conda2pip(ymlFile="syncopy.yml", return_lists=False):
    """
    Convert conda environment YAML file to pip-style requirements.txt
    
    Parameters
    ----------
    ymlFile : str
        Name of (may include path to) conda environment YAML file. 
    return_lists : bool
        If `True`, lists of package names `required` and `testing` are returned
        
    Returns
    -------
    required : list
        List of strings; names of required packages as indicated in input
        `ymlFile` (see Notes for details; only returned if `return_lists` is `True`)
    testing : list
        List of strings; names of packages only needed for testing and development
        as indicated in input `ymlFile` (see Notes for details;  only returned 
        if `return_lists` is `True`)
        
    Notes
    -----
    This function always generates the file "requirements.txt" and possibly 
    "requirements-test.txt" inside the directory it is executed in. **WARNING** 
    Any existing files will be overwritten without confirmation!
    
    Please use comments inside the yml input-file containing the words "test" or 
    "optional" to differentiate between required/elective packages, e.g., 
    
    ```yaml
    dependencies:
      # runtime requirements
      - numpy >= 1.15
      - scipy >= 1.5, < 1.6
      # testing
      - matplotlib >= 3.3, < 3.5
      - pip:
        # optional
        - sphinx_automodapi
    ```
    
    Then calling ``conda2pip`` creates two files: "requirements.txt"
    
    ```text
    # This file was auto-generated by conda2pip.py on 05/10/2020 at 11:11:21. 
    # Do not edit, all of your changes will be overwritten. 
    sphinx_automodapi
    matplotlib >= 3.3, < 3.5    
    ```
    
    and "requirements-test.txt":
    
    ```text
    # This file was auto-generated by conda2pip.py on 05/10/2020 at 11:11:21. 
    # Do not edit, all of your changes will be overwritten. 
    sphinx_automodapi
    matplotlib >= 3.3, < 3.5        
    ```
    
    Please refer to the 
    `conda documentation <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#sharing-an-environment>`_ 
    for further information about conda environment files. 
    """
    
    # Initialize YAML loader and focus on "dependencies" section of file
    with ruamel.yaml.YAML() as yaml:
        with open(ymlFile, "r") as fl:
            ymlObj = yaml.load(fl)
    deps = ymlObj["dependencies"]

    # If present, find "pip" requirements section    
    pipIndex = None
    for index, key in enumerate(deps):
        if not isinstance(key, str):
            pipIndex = index
    
    # Start by processing "pip" packages (if present) to find required/optional packages
    required = []
    testing = []
    if pipIndex:
        pipDeps = deps.pop(pipIndex)
        pipReq, pipTest = _process_comments(pipDeps["pip"])
        required += pipReq
        testing += pipTest

    # Now process all conda packages and differentiate b/w required/testing    
    condaReq, condaTest = _process_comments(deps)
    required += condaReq
    testing += condaTest
    
    # Remove specific Python version (if present) from required packages, since 
    # `pip` cannot install Python itself 
    pyReq = [pkg.startswith("python") for pkg in required]
    if any(pyReq):
        required.pop(pyReq.index(True))

    # Prepare info string to write to *.txt files    
    msg = "# This file was auto-generated by {} on {}. \n" +\
        "# Do not edit, all of your changes will be overwritten. \n"
    msg = msg.format(os.path.basename(__file__), 
                     datetime.datetime.now().strftime("%d/%m/%Y at %H:%M:%S"))

    # Save `required` and `testing` lists in *.txt files
    with open("requirements.txt", "w") as f:
        f.write(msg)
        f.write("\n".join(required))
    if len(testing) > 0:
        with open("requirements-test.txt", "w") as f:
            f.write(msg)
            f.write("\n".join(testing))

    # If wanted, return generated lists            
    if return_lists:
        return required, testing


def _process_comments(ymlSeq):
    """
    Local helper performing the heavy YAML sequence lifting
    """

    # Replace any conda-specific packages with their pip equivalents (note: this 
    # does *not* change the no. of elements, so `cutoff` below is unharmed!)
    for condaPkg, pipPkg in pkgConvert.items():
        pkgFound = [pkg.startswith(condaPkg) for pkg in ymlSeq]
        if any(pkgFound):
            pkgIdx = pkgFound.index(True)
            pkgEntry = ymlSeq[pkgIdx].replace(condaPkg, pipPkg)
            ymlSeq[pkgIdx] = pkgEntry

    # Cycle through comment items to determine `cutoff` index, i.e., line-number 
    # of comment containing one of the keywords; then split packages into 
    # required/testing accordingly    
    cutoff = None    
    for lineno, tokens in ymlSeq.ca.items.items():
        for token in [t[0] if isinstance(t, list) else t for t in tokens]:
            if any([keyword in token.value.lower() if token is not None else False for keyword in commentKeys]):
                if lineno == 0:
                    cutoff = max(0, token.end_mark.line - ymlSeq.lc.data[0][0] - 1)
                else:
                    cutoff = lineno + 1
                break
            
    # If no testing packages are present, `cutoff` is `None` and ``needed == ymlSeq``
    needed = ymlSeq[:cutoff]
    optional = []
    if cutoff is not None:
        optional = ymlSeq[cutoff:]
    
    return needed, optional


# If executed as script, process default YAML file "syncopy.yml"
if __name__ == "__main__":
    conda2pip()
