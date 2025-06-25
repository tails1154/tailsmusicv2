#!/bin/bash

rm -rf docs/*
doxygen
cp -r docs/html/* docs
rm -rf docs/html
rm -rf docs/tex
