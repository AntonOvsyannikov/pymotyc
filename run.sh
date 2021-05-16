#!/bin/sh

case "$1" in

  mongo)
    docker network create pymotyc
    docker run --network pymotyc --name mongo -p "27017:27017" -d mongo:4.4
    docker run --network pymotyc --name mongo-express -p "8081:8081" --restart always -d mongo-express
    ;;

  cleanup)
    docker rm -f mongo mongo-express
    docker network rm pymotyc
    ;;

  build)
    rm -rf build dist
    python3 -m build
    ;;

  upload_test)
    source .tokens.sh
    python3 -m twine upload -u __token__ -p ${PYPI_TOKEN_TEST} --repository testpypi dist/*
    ;;

  upload)
    source .tokens.sh
    python3 -m twine upload -u __token__ -p ${PYPI_TOKEN} dist/*
    ;;

esac