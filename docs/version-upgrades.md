
# Version Upgrades

When the software updates significantly (typically, every minor
release) you need to rebuild the database.  This is because the
databaase schema, or the data stored in the database, have changed.

To make this less painful I try to:

 1. Minimize changes that impact data entered via the diary.

 2. Provide a script that automates the transfer of non-activity data
    from the old database.

So to upgrade to a new version you probably need to do the following
steps:

 * Locate the correct upgrade script in `ch2/migrate/upgrade`.  These
   are named by version.  You can find the current version of choochoo
   by running the command `ch2 -V`.

 * **Modify** the script to reflect your own preferences.  This will
   include filenames (at the top of the file) and constants (at the
   bottom).

 * Run the script.

 * Reload your activity data using the command `ch2 activities`

Note that the previous version's database is left intact.  So you
should not lose any data in this process - at worst you can always
return to using the previous version of the software.

## Resets

Sometimes it is useful to wipe the existing database and reload
activities.  This is a similar process to upgrading (above), but uses
the scripts in `ch2/migrate/reset` and leaves a copy of the previous
database with the postfix `-backup`.

