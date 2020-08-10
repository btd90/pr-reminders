# PR Reminders

Python script capable of reminding users/authors on Pull Requests in Bitbucket to take action.
This script calls the Bitbucket 1.0 API to query for open Pull Requests, and will post a comment against the PR using the following criteria:

* PR is older than 10 day - comment suggesting author to close PR and perform further work
* No activity on PR for more than 2 days:
  * PR has a failing build - comment reminding author to make fixes
  * PR has no reviewers - comment reminding author to add reviewers
  * PR has reviewers yet to review - comment reminding reviewers to take a look
  * PR has reviewers that have approved review - comment reminding author to merge

Included is a 'reminders' cron entry that will trigger this script to run overnight.

## Prerequisites

To run the script you will need python 2.7.
Untested on python 3+.

## Setup

* `git clone <repository-url>` this repository
* Place move reminders.py somewhere on the filesystem to execute
* `crontab -e` and copy cron/reminders content to point to the location chosen
* Modify reminders.py and set values for Bitbucket url, Project and Repository names

## Testing / Development

A number of JSON mock responses and configuration for httpd are also included under json/ and conf/ directories.
These can be served by a webserver (such as httpd) to test this script if desired.

### Testing with Mock Responses

To provide mock responses for use by the script:
* `yum install httpd`
* Copy conf/reminders.conf to httpd/conf.d/ directory
* Copy files under json/ directory to server root directory (if different from default then update reminders.conf)
* `systemctl restart httpd`
* `curl -I 'localhost/rest/api/1.0/application-properties'` to verify
* `python reminders.py` to run script
