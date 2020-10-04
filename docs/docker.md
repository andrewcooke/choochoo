
# Docker Cookbook

**Important** - the use of Docker has changed so quickly that these notes are
now out of date.  The [install](index.md) notes ar emore reliable.

This page contains various hints, tips and examples on how you can
configure and use the Docker images.

## Configuration

### All Data In Container

    > docker run -p 127.0.0.1:8000:8000 -p 127.0.0.1:8001:8001 \
      andrewcooke/choochoo:latest

Running the container in this way, all your data - both the FIT files
and the database of statistics - is stored inside the Docker image.
This is not ideal because it is difficult to upgrade to a new version
of the code (if you change to a new image you lose you data), hard to
backup your data, and easy to accidentally delete the data when you
delete unused Docker images.

### Data On Local Disk

    > docker run -p 127.0.0.1:8000:8000 -p 127.0.0.1:8001:8001 \
      -v ~/.ch2:/data andrewcooke/choochoo:latest

This mounts the given path (`~/.ch2` here, but it could be whatever
you want) to the `/data` directory inside the image (which is where
data are stored).

When the image saves data to `/data` it will write to your local disk,
rather than inside the Docker image.

This makes it easier to backup your data and to upgrade to a newer
version of the code (you can download a new image and mount the old
data there).

The main drawback of this approach (for a single user on their local
computer) is that anything written to disk is owned by `root`.

### Data In Volume

    > docker volume create choochoo-data

This creates a named volume (something like a disk) where you can
store data.  It can be mounted in the same way as the directory above:

    > docker run -p 127.0.0.1:8000:8000 -p 127.0.0.1:8001:8001 \
      -v choochoo-data:/data andrewcooke/choochoo:latest

### Separate PostgreSQL Server

By default Choochoo uses the SQLite database which reads from a file
in `/data`.  By defining the appropriate connection URI we can change
this:

    > cat docker-compose.yml
    version: '3'
    services:
      ch2:
        image: 'andrewcooke/choochoo:latest'
        container_name: 'choochoo'
        ports:
          - '127.0.0.1:8000:8000'
          - '127.0.0.1:8001:8001'
        environment:
          - 'CH2_DKR_URI=postgresql://postgres@postgresql/activity-0-34'
        depends_on:
          - 'pg'
      pg:
        image: 'postgres:11.8-alpine'
        container_name: 'postgresql'
        shm_size: '1g'
        environment:
          - 'POSTGRES_HOST_AUTH_METHOD=trust'
    > docker-compose up

Here, using `docker-compose` we start a PostgreSQL server in a
separate image and use that as the statistics database (the examples
above all use an SQLite3 database which is stored in `/data`).

Note that the database URI refers to the address `postgresql` - this
is the address of the machine that the `postgresql` container is
running on (set by `container_name`).

Because system data are stored within the `choochoo` container, and
database data within the `postgresql` container you must **not**
delete these containers.

### Database In Volume

We can create a second volume for the PostgreSQL data.

    > docker volume create postgresql-data
    > cat docker-compose.yml
    version: '3'
    services:
      ch2:
        image: 'andrewcooke/choochoo:latest'
        container_name: 'choochoo'
        ports:
          - '127.0.0.1:8000:8000'
          - '127.0.0.1:8001:8001'
        volumes:
          - 'choochoo-data:/data'
        environment:
          - 'CH2_DKR_DB_URI=postgresql://postgres@postgresql/activity-0-34'
        depends_on:
          - 'pg'
      pg:
        image: 'postgres:11.8-alpine'
        container_name: 'postgresql'
        shm_size: '1g'
        ports:
          - '127.0.0.1:5432:5432'
        environment:
          - 'POSTGRES_HOST_AUTH_METHOD=trust'
        volumes:
          - 'postgresql-data:/var/lib/postgresql/data'
    volumes:
      choochoo-data:
        external: true
      postgresql-data:
        external: true
    > docker-compose up

Because no data are stored on the container, we can discard the
containers after use.

## Recipes

### Copy Files Onto A Disk Image

    > docker run --rm \
       -v choochoo-data:/data \
       -v ~/.ch2/permanent:/permanent \
       opensuse/leap \
       cp -rv /permanent/monitor /data/permanent/

This mounts the `choochoo-data` volume at `/data` and
`~/.ch2/permanent` (the default location for FIT file storage on the
local disk to `/permanent` before running a command to copy the files
across.  I used the `opensuse/leap` image because that matches my
development machine (so is what I am used to), but you could use
almost anything.

### Run The psql Client

    > docker exec -it postgresql psql -Upostgres activity-0-34

Assuming that the postgesql container is already running.

## Development

The `dkr` directory in the source tree contains various scripts and
configurations, including the `Dockerfile` used to build the standard
image.
