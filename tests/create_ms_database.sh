set -ex
SQL_COMMAND="sqlcmd -S tcp:$MSSQL_HOST,$MSSQL_1433_TCP_PORT -U sa -P $DATABASE_PASSWORD -b"

# Wait for server (not required when running tox locally but circle doesn't support healthcheck)
while ! $SQL_COMMAND -Q "SELECT 1" >/dev/null ; do
    printf '.'
    sleep 1
done

# Create MS database
SCRIPT=$(mktemp)
cat >$SCRIPT <<EOF
PRINT N'Creating $DATABASE_NAME...';
GO
CREATE DATABASE [$DATABASE_NAME]
GO
CREATE SCHEMA [$DATABASE_NAME]
    AUTHORIZATION [dbo];
GO
CREATE LOGIN $DATABASE_USER WITH PASSWORD = '$DATABASE_PASSWORD';
GO
USE [$DATABASE_NAME]
GO
CREATE USER [$DATABASE_USER] FROM LOGIN [$DATABASE_USER];
GO
exec sp_addrolemember 'db_owner', '$DATABASE_USER';
SELECT 1
GO
EOF
$SQL_COMMAND -i $SCRIPT >/dev/null
