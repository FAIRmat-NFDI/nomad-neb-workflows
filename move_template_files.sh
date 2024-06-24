#!/bin/sh

rsync -avh nomad-neb-workflows/ .
rm -rfv nomad-neb-workflows
