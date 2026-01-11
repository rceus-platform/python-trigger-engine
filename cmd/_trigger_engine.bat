
@echo off

set REPO_NAME=python-trigger-engine

rem Run the batch file from the cmd directory
call "%github-local-directory%\%REPO_NAME%\cmd\run.cmd" %1
