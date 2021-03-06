#!/usr/bin/env python3

"""
Test performing the following scenario on behalf of multiple users in parallel:
- each user cyclically updates and reads his/her own verkey.

To run the test execute this python script providing the following parameters:
-u <NUMBER_OF_USERS> or --users <NUMBER_OF_USERS>
-i <NUMBER_OF_ITERATIONS> or --iterations <NUMBER_OF_ITERATIONS>
-t <TIMEOUT_IN_SECONDS> or --timeout <TIMEOUT_IN_SECONDS> (optional parameter)

Examples:

test_users_write_and_read_own_keys -u 8 -i 10 -t 60

test_users_write_and_read_own_keys --users 20 --iterations 50
"""

import argparse
import os
from concurrent import futures
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

from stp_core.common.log import getlogger

from sovrin_client.utils.user_scenarios import generateNymsData, \
    NymsCreationScenario, KeyRotationAndReadScenario

STEWARD1_SEED = b"000000000000000000000000Steward1"

logger = getlogger()


def parseArgs():
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--users",
                        type=int,
                        required=True,
                        dest="users",
                        help="number of users")

    parser.add_argument("-i", "--iterations",
                        type=int,
                        required=True,
                        dest="iterations",
                        help="number of iterations")

    parser.add_argument("-t", "--timeout",
                        type=int,
                        dest="timeout",
                        help="timeout in seconds")

    return parser.parse_args()


def main(args):
    numOfUsers = args.users
    numOfIterations = args.iterations
    timeout = args.timeout

    users = generateNymsData(numOfUsers)

    logDir = os.path.join(os.getcwd(), "test-logs-{}".format(
        datetime.now().strftime("%Y-%m-%dT%H-%M-%S")))

    with ProcessPoolExecutor(numOfUsers) as executor:
        usersIdsAndVerkeys = [(user.identifier, user.verkey)
                              for user in users]

        nymsCreationScenarioFuture = \
            executor.submit(NymsCreationScenario.runInstance,
                            seed=STEWARD1_SEED,
                            nymsIdsAndVerkeys=usersIdsAndVerkeys,
                            logFileName = os.path.join(
                                logDir,
                                "nyms-creator-{}".format(
                                    STEWARD1_SEED.decode())))

        nymsCreationScenarioFuture.result(timeout=timeout)
        logger.info("Created {} nyms".format(numOfUsers))

        keyRotationAndReadScenariosFutures = \
            [executor.submit(KeyRotationAndReadScenario.runInstance,
                             seed=user.seed,
                             iterations=numOfIterations,
                             logFileName=os.path.join(
                                 logDir,
                                 "user-{}".format(user.seed.decode())))
             for user in users]

        futures.wait(keyRotationAndReadScenariosFutures,
                     timeout=timeout)

        failed = False
        for future in keyRotationAndReadScenariosFutures:
            ex = future.exception(timeout=0)
            if ex:
                failed = True
                logger.exception(ex)

        if failed:
            logger.error("Scenarios of some users failed")
        else:
            logger.info("Scenarios of all users finished successfully")

    logger.info("Logs of worker processes were also written to {}"
                .format(logDir))


if __name__ == "__main__":
    main(parseArgs())
