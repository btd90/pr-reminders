#!/bin/python
#
# This script is used primarily to help progress Bitbucket Pull Requests that
# have gone 'stale' and need attention.
#
# The Bitbucket 1.0 REST/BUILD API is used to firstly status Bitbucket, then
# GET all OPEN Pull Requests, fetch details regarding their activity and POST
# a relevant comment to alert authors/reviewers with suggestions to progress
# the review. Build status against the Pull Request is also fetched if required.
#

import datetime
import requests
import json

BITBUCKET_URL = 'http://localhost:80'
PROJECT = 'PRJ'
REPOSITORY = 'REPO'

BUILD_ENDPOINT = '/rest/build-status/1.0/commits/'
STATUS_ENDPOINT = '/rest/api/1.0/application-properties'
REST_ENDPOINT = '/rest/api/1.0/projects/' + PROJECT + '/repos/' + REPOSITORY
PULL_REQUESTS_ENDPOINT = '/pull-requests/'

ACTIVITIES = '/activities'
COMMENTS = '/comments'
COMMITS = '/commits'
PULL_REQUESTS = '/pull-requests'

# Datetime Constants
TODAY = datetime.datetime.today()
TWODAYS = datetime.timedelta(days=2)
TENDAYS = datetime.timedelta(days=10)

def main():
    # Check Bitbucket is accessible
    statusBitbucket();

    # Fetch open PRs and extract ids
    prIDs = fetchOpenPRs();

    # Iterate over PR ID values
    for prID in prIDs:
        # Fetch content for each PR
        url = BITBUCKET_URL + REST_ENDPOINT + PULL_REQUESTS_ENDPOINT + str(prID);
        pullRequest = queryBitbucket(url);
        pullRequestJSON = pullRequest.json();

        # Calculate time since last update to PR
        checksRequiredPR = analyzePRTimes(prID, pullRequestJSON);

        # Calculate last time since comment/review action
        checksRequiredAction = analyzeActionTimes(prID, url);

        # Run checks
        if (checksRequiredPR and checksRequiredAction):
            if checkBuildStatus(prID, url):
                continue;
            elif checkReviewers(prID, pullRequestJSON):
                continue;
            elif checkApprovals(prID, pullRequestJSON):
                continue;
            elif checkMerge(prID, pullRequestJSON):
                continue;
            else:
                # No action required
                continue;

    # Return success
    exit(0);


# Perform GET Request
def queryBitbucket(url):
    try:
        response = requests.get(url);
    except:
        exit(1);

    # Exit with failure if bad status code returned
    if (response.status_code != requests.codes.ok):
        exit(1);

    return response;


# Perform POST
def postToBitbucket(prID, comment):
    # Prepare to POST
    url = BITBUCKET_URL + REST_ENDPOINT + PULL_REQUESTS_ENDPOINT + str(prID) + COMMENTS;
    data = { "text": comment };

    try:
        response = requests.post(url, data);
    except:
        exit(1);

    # Exit with failure if bad status code returned
    if (response.status_code != requests.codes.ok):
        exit(1);

    return;


# Stutus Bitbucket
def statusBitbucket():
    url = BITBUCKET_URL + STATUS_ENDPOINT;
    queryBitbucket(url);


# Fetch Pull Requests (defaults to OPEN PRs only)
def fetchOpenPRs():
    idVals = [];
    url = BITBUCKET_URL + REST_ENDPOINT + PULL_REQUESTS;
    response = queryBitbucket(url);

    # Iterate through response to get PR IDs
    content = response.json();
    for key, prArray in content.items():
        if (key == 'values' and prArray):
            for pr in prArray:
                idVals.append(pr['id']);
            break;

    # No Open PRs, exit
    if not idVals:
        exit(0)

    return idVals;


# Using datetime objects inspect PR age and update duration
def analyzePRTimes(prID, pullRequestJSON):
    createdDate = '';
    updatedDate = '';
    runChecks = False;

    # Store creation and updated dates
    for key, value in pullRequestJSON.items():
        if (key == 'createdDate'):
            createdDate = datetime.datetime.fromtimestamp(value);
        elif (key == 'updatedDate'):
            updatedDate = datetime.datetime.fromtimestamp(value);

    # PR should not be missing these values, exit with failure
    if not createdDate or not updatedDate:
        exit(1)

    # Store time differences and period last updated
    prAge = TODAY - createdDate;
    updatePeriod = updatedDate - createdDate;

    # Check if PR is older than 10 days
    if (prAge > TENDAYS):
        suggestDecline(prID);
    elif (updatePeriod > TWODAYS):
        runChecks = True;

    return runChecks;


# Using datetime objects inspect PR activity age
def analyzeActionTimes(prID, url):
    runChecks = True;
    activityUrl = url + ACTIVITIES;
    response = queryBitbucket(activityUrl);

    # Iterate through response to get activity content
    content = response.json();
    for key, activityArray in content.items():
        if (key == 'values' and activityArray):
            for activity in activityArray:
                action = activity['action'];
                createdDate = datetime.datetime.fromtimestamp(activity['createdDate']);

                # Check if desired activity occured < 2 days ago
                if (action == 'COMMENTED' or action == 'REVIEWED' or action == 'APPROVED'):
                    activityAge = TODAY - createdDate;
                    if (activityAge < TWODAYS):
                        runChecks = False;
                        break;
            break;

    return runChecks;


# Alert author to decline PR
def suggestDecline(prID):
    delim = "\n";
    msg = [];

    # Prepare comment
    msg.append("Good day sir,");
    msg.append("It appears your review has gone rather stale!");
    msg.append("May I suggest declining and performing further work?");
    comment = delim.join(msg);

    # POST Comment to server
    postToBitbucket(prID, comment);


# Verify if last build passed
def checkBuildStatus(prID, url):
    lastCommitId = '';

    # Prepare comment
    delim = "\n";
    msg = [];
    msg.append("Sir,");
    msg.append("I don't mean to alarm you but your current build is rather broken!");
    msg.append("Some fixes should be in order.");
    comment = delim.join(msg);

    # Get PR commit (ordered by latest)
    commitUrl = url + COMMITS;
    response = queryBitbucket(commitUrl);
    commits = response.json();

    # Extract commit Id from response
    for key, commitArray in commits.items():
        if (key == 'values' and commitArray):
            latestCommit = commitArray[0];
            lastCommitId = latestCommit['id'];
            break;

    # No commits to check, something wrong with build
    if not lastCommitId:
        # POST Comment to server
        postToBitbucket(prID, comment);
        return True;

    # Fetch build status for commit (ordered by latest)
    url = BITBUCKET_URL + BUILD_ENDPOINT + str(lastCommitId);
    response = queryBitbucket(url);
    buildStats = response.json();

    # Check build status for commit
    for key, buildArray in buildStats.items():
        if (key == 'values' and buildArray):
            latestBuild = buildArray[0];
            if (latestBuild['state'] != 'SUCCESSFUL'):
                # POST Comment to server
                postToBitbucket(prID, comment);
                return True;
            break;

    return False;


# Verify if PR has reviewers
def checkReviewers(prID, pullRequestJSON):
    needsReviewers = False;
    author = "";
    delim = "\n";
    msg = [];

    # Find reviewers
    for key, value in pullRequestJSON.items():
        if key == 'reviewers' and not value:
            needsReviewers = True;
        elif key == 'author':
            author = value['user']['name'];

    if needsReviewers:
        # Prepare comment
        msg.append("Pardon me, @" + author + ",");
        msg.append("Your pull request would benefit from a reviewer or two.");
        msg.append("May I suggest adding some?");
        comment = delim.join(msg);

        # POST Comment to server
        postToBitbucket(prID, comment);
        return True;

    return False;


# Verify reviewers have responded
def checkApprovals(prID, pullRequestJSON):
    reviewers = [];
    reviewerDelim = ", @";
    delim = "\n";
    msg = [];

    # Find reviewers that require action
    for key, reviewerArray in pullRequestJSON.items():
        if (key == 'reviewers' and reviewerArray):
            for reviewer in reviewerArray:
                if reviewer['role'] == 'REVIEWER' and reviewer['status'] == "UNAPPROVED":
                    reviewers.append(reviewer['user']['name']);
            break;

    if reviewers:
        # Prepare comment
        msg.append("Ehem, @" + reviewerDelim.join(reviewers));
        msg.append("Your input is required to progress this review.");
        msg.append("Kindly address this at your earliest convenience.");
        comment = delim.join(msg);

        # POST Comment to server
        postToBitbucket(prID, comment);
        return True;

    return False;


# Verify PR can be merged
def checkMerge(prID, pullRequestJSON):
    canMerge = True;
    author = "";
    delim = "\n";
    msg = [];

    # Find reviewers (by reaching this point we know the build is passing)
    for key, value in pullRequestJSON.items():
        if key == 'author':
            author = value['user']['name'];
        elif (key == 'reviewers' and value):
            for reviewer in value:
                if reviewer['role'] == 'REVIEWER' and reviewer['status'] != "APPROVED":
                    canMerge = False;

    # Check for issues
    if canMerge:
        # Prepare comment
        msg.append("Pardon me, @" + author + ",");
        msg.append("With a passing build and approved reviewers, I see no reason not to merge this pull request!");
        msg.append("Would you agree?");
        comment = delim.join(msg);

        # POST Comment to server
        postToBitbucket(prID, comment);
        return True;

    return False;


# Main
if __name__ == '__main__':
    main()
