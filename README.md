# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# smartcdc.ai is a Change Data Capture (CDC) tool.
Provides APIs for creating customer database connections to recieve WAL Events

## Running locally

1. `git clone git@github.com:smartcdc-ai/backend.git` 
2. `cd backend`
4. Go into virtual environment: `python -m venv venv` and then `source venv/bin/activate`. This ensures Python keeps packages isolated and keeps your system secure. 
3. Ensure `smart_cdc_prod_admin` MySQL DB exists. 
  - `mysql -u root -p` password: root (or whatever you local MySQL dev credentials are)
  - `CREATE DATABASE smart_cdc_prod_admin;`
  - Confirm: `SHOW DATABASES LIKE 'smart_cdc_prod_admin';`
    ```mysql
      +------------------------+
      | Database (smart_cdc_prod_admin) |
      +------------------------+
      | smart_cdc_prod_admin            |
      +------------------------+
      1 row in set (0.01 sec)
    ```

3. Create [Alembic](https://flask-alembic.readthedocs.io/en/latest/) migration: `alembic revision --autogenerate -m "First migration for MySQL"`
4. And then run the migration:
```bash
alembic upgrade head
```

5. Get `.env` file from AWS secrets manager → **AWS Secrets Manager > Secrets > /smartcdc/local/smartcdc-backend/.env** and put it in .env file in the root directory.

6. You can now run Flask app locally:
```bash
flask run --port=5000
```

### Frontend app
- `cd ../` change out of the backend directory.
- `git clone git@github.com:smartcdc-ai/frontend.git`
- `cd frontend`
- `npm install`
- `npm run start`

## Running Docker locally
1. Ensure you have docker installed:
`docker --version` if not see [Install Mac](https://docs.docker.com/desktop/setup/install/mac-install/) or [Install Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
2. **IMPORTANT** Ensure `DB_HOST` in `.env` is set to `host.docker.internal`, ex: `DB_HOST=host.docker.internal`. 
3. Then simply run: `docker-compose up -d --build`



## AWS Deployments
The Backend is hosted on AWS Elastic Container Service (ECS) Fargate instances. Below is diagram of the infrustructure.
![smartcdc AI AWS ECS Infrastructure Diagram.png](https://space-rocket.com/ecs-terraform-diagram.png)

Deployments are automatically done through CI/CD. Below are steps to directly interact with the Fargate containers, log into the RDS Aurora MySQL Cluster, and run migrations. 

#### Step 1: Configure AWS CLI
1. [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

#### Step 2: Create an IAM User for Terraform
2. **Create an IAM User**:
- Log in as your Root account or user with `AdministratorAccess`
- Go to **IAM** in the AWS Management Console.
- Click **Users**, then **Add Users**.
- Enter a meaningful **User Name** (e.g., `YOUR_NAME-admin`).
- Select **Provide user access to the AWS Management Console**.
- Click **Next: Permissions**.

3. **Attach Permissions**:
- Select **Attach existing policies directly**.
- Attach `AdministratorAccess` or a custom policy for limited permissions.

4. **Finalize User Creation**:
- Add optional tags under **Next: Tags**.
- Click **Create User**.
- Under the user **Summary**, click **Create access key**.
- Select **Command Line Interface (CLI)** access.
- Save the **Access Key ID** and **Secret Access Key** or download the `.csv` file.

#### Step 3: Configure AWS CLI with the New IAM User
Configure the AWS CLI with the new IAM user's credentials:

1. **Open Terminal**.
2. **Run Configuration Command**:
```bash
aws configure --profile YOUR_NAME-admin
```

Enter the following when prompted:
- **AWS Access Key ID**: Provide the access key.
- **AWS Secret Access Key**: Provide the secret key.
- **Default region name**: Specify the region (e.g., us-west-1).
- **Default output format**: Enter `json` or leave empty for default.

#### Step 4: Test the New Profile
1. **Set the Profile**:
```bash
export AWS_PROFILE=YOUR_NAME-admin
```

2. **Verify Setup**:
```bash
aws sts get-caller-identity
```


## Shell into a container running at Fargate
Replace arn with task arn (see screen shot)
![How to get ARN of task](https://space-rocket-hugo-woeflz.s3.us-east-1.amazonaws.com/Screenshot+2024-12-30+at+2.23.06+AM.png)

```bash
aws ecs execute-command  \
      --region us-east-1 \
      --cluster prod-smart-cdc-flask-backend-ecs-cluster \
      --task arn:aws:ecs:us-east-1:123456789101:task/prod-smart-cdc-flask-backend-ecs-cluster/57f12b90586c4cc89aae6df406fc9d43 \
      --container smart-cdc-flask-backend \
      --command "/bin/sh" \
      --interactive
```

Once in container shell, you can securely connect to the RDS Aurora MySQL. This is the only way to access it.

```bash
mysql -h [VALUE FROM /smart-cdc/prod/smart-cdc-flask-backend/DB_HOST] -u [VALUE FROM /smart-cdc/prod/smart-cdc-flask-backend/DB_USER] -p
```

`DB_PASSWORD` = VALUE FROM `/smart-cdc/prod/smart-cdc-flask-backend/DB_PASSWORD`

See screenshot how to get the values:
![get db creds](https://space-rocket-hugo-woeflz.s3.us-east-1.amazonaws.com/parameterstore.png)

## Migrations
Update `backend/alembic.ini` `sqlalchemy.url` with value from AWS Parameter: `/smart-cdc/prod/smart-cdc-flask-backend/SQLALCHEMY_URL`. 

Screenshot for how to get the values:
![get SQLALCHEMY_URL](https://space-rocket-hugo-woeflz.s3.us-east-1.amazonaws.com/sqlalchemyurl.png)


Then run revision command to generate a migration:
```bash
alembic revision --autogenerate -m "New migration for MySQL"
```

And then run the migration:
```bash
alembic upgrade head
```

## Replication Slots

Check Active Replication Slots
```
SELECT slot_name, active_pid FROM pg_replication_slots;
```

Terminate a Specific Replication Slot Process
```
SELECT pg_terminate_backend(active_pid) FROM pg_replication_slots WHERE slot_name = 'smartcdc_slot';
```


