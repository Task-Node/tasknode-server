# FastAPI Boilerplate Template App

This is a basic boilerplate template for a [FastAPI](https://fastapi.tiangolo.com/lo/) based app for deployment using the [Serverless](https://www.serverless.com/) framework. This is meant to provide a sane starting point for larger projects using FastAPI

## Libraries used

I make use of the following libraries here:

- [Serverless](https://www.serverless.com/) - for handling deployment of the project to AWS Lambda/API Gateway
  - [serverless-prune-plugin](https://www.serverless.com/plugins/serverless-prune-plugin) - to purge previous deployed versions of functions from AWS lambda
- [cross-env](https://www.npmjs.com/package/cross-env) - for running node scripts across platforms
- [Poetry](https://python-poetry.org/) - For python packaging and dependency management (an alternative to virtualenv + pip)
- [PostgreSQL](https://www.postgresql.org/) - relational database
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM for managing database
- [Alembic](https://alembic.sqlalchemy.org/en/latest/) - For database migrations
- [Pytest](https://pytest.org) - For running unit tests
- [Black](https://pypi.org/project/black/) - An opinionated python linter

## Python version

This project uses Python version 3.9. I have not tested it with other versions of Python, but it should work with 3.9+.

## Requirements

If you intend to deploy using the [Serverless](https://www.serverless.com/) framework, first install serverless globally using command:

```
npm install -g serverless
```

If you don't plan to use serverless to deploy your app, you can delete the package.json, package-lock.json and serverless.yml files.

You will also need Python 3.9, poetry and PostgreSQL installed locally to run this project.

## Customizing

Throughout this project, I use the project name `my-fastapi-app`. You will want to find/replace this with your own project name.

# Getting started

1. Make sure you have Python3.9 installed locally. Install poetry on your machine (instructions [here](https://python-poetry.org/docs/)). Then run command to initialize a new environment (you will also run this command when subsequently opening the project to navigate to this already-created environment).:

   ```
   poetry shell
   ```

   Next, run the following command to install dependencies:

   ```
   poetry install
   ```

2. Make sure you have PostgreSQL (server and command line tool) installed locally. Add an empty local database + test database (code below assumes you already have the postgres command line tools and a local server setup):

   ```
   createdb tasknode
   createdb tasknode_test
   ```

3. Initialize DB

```
 python manage.py db init
 # This is for local. For DEV or PRD, run:
 # env=Development python manage.py db init
 # env=Production python manage.py db init
```

3. Run migrate (this doesn't actually modify your database just yet... it just generates a migration script that we will run in the next step)

   Note: this will setup with the dummy Foo model... if you are just getting started, you should run these commands right away to make sure everything is working. After that, see steps in section "Resetting the database" to start with a fresh DB.

   ```
   python manage.py db migrate "first migration"
   # This is for local. For DEV or PRD, run:
   # env=Development python manage.py db migrate "first migration"
   # env=Production python manage.py db migrate "first migration"
   ```

4. Upgrade database (this is the step where the actual DB tables get modified/created)

   ```
   python manage.py db upgrade
   # This is for local. For DEV or PRD, run:
   # env=Development python manage.py db upgrade
   # env=Production python manage.py db upgrade
   ```

5. Run unit tests

   ```
   pytest
   ```

6. Start the server

   ```
   python manage.py runserver
   # env=Development python manage.py runserver
   # env=Production python manage.py runserver
   ```

   Once the server is running, go to http://127.0.0.1:5000 to see the swagger docs and play around.

## Resetting the database

The steps above create a table called Foo. I provided this as an example template, but you probably want to define your own tables. To reverse the steps above:

1. Run this command to downgrade your database

```
python manage.py db downgrade
```

2. Delete the python script that was generate inside of the alembic/versions folder

3. Create your own models/tabels and rerun the steps above!

# Deploying via Serverless

To deploy, you will first need to create a remote database and set the database connection strings up. It is recommended that you use something like AWS Secrets Manager to store sensitive info like connection strings. However, at the very least, keep this info out of checked in files. You can create a file in the config folder called `local_overrides.py` that is already ignored by .gitignore and set the variables there if you are just getting started and haven't configured secrets manager yet. For example, you can setup the `local_overrides.py` file like this:

```
from .local import Local as LocalDefault
from .development import Development as DevelopmentDefault
from .production import Production as ProductionDefault

class Local(LocalDefault):
    pass

class Development(DevelopmentDefault):
    SQLALCHEMY_DATABASE_URI: str = "postgres://username:password@foooobar.cluster-abcdefhijk.us-east-1.rds.amazonaws.com:5432/my-fastapi-app-dev"

class Production(ProductionDefault):
    SQLALCHEMY_DATABASE_URI: str = "postgres://username:password@foooobar.cluster-abcdefhijk.us-east-1.rds.amazonaws.com:5432/my-fastapi-app-prod"
```

## Deploy commands

Deploy to dev with command:

```
npm run deploy
```

and to production with:

```
npm run deploy:prod
```

When the job finishes deploying, it should give you a URL:

```
✔ Service deployed to stack my-fastapi-app-dev (76s)

endpoint: ANY - https://abcdefghij.execute-api.us-east-1.amazonaws.com/dev/{proxy+}
```

Navigate to the deployed docs by opening the link in a browswer, but replacing `{proxy+}` with `docs`.

Undeploy with commands `npm run undeploy` and `npm run undeploy:prod` respectively (warning: this will remove the entire serverless stack, including any resources you created via the serverless.yml file).

# Linting

This codebase uses [Black](https://pypi.org/project/black/) for linting. To run the linter, run command:

```
npm run lint
```
