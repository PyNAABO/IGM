from iaf.core.bot import IAFBot
from iaf.features import UnfollowFeature, FollowFeature


def main():
    bot = IAFBot()
    if bot.start(headless=True):
        if bot.login():
            # Execution Cycle
            bot.run_feature(UnfollowFeature)

            bot.random_sleep(5, 10)

            bot.run_feature(FollowFeature)

            bot.close()
    else:
        # Schedule check failed or other start issue
        pass


if __name__ == "__main__":
    main()
