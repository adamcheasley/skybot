" seen.py: written by sklnd in about two beers July 2009"

import time
from datetime import datetime
from datetime import timedelta

from util import hook, timesince


def db_init(db):
    "check to see that our db has the the seen table and return a connection."
    db.execute("create table if not exists seen(name, time, quote, chan, "
               "primary key(name, chan))")
    db.commit()


@hook.singlethread
@hook.event('PRIVMSG', ignorebots=False)
def seeninput(paraml, input=None, db=None, bot=None):
    """Kick users that have not chatted for over a week.
    Bans users who haven't chatted in two weeks
    """
    db_init(db)
    # add/update the user who has just spoken to the seen table
    db.execute("insert or replace into seen(name, time, quote, chan)"
               "values(?,?,?,?)", (input.nick.lower(), time.time(), input.msg,
                                   input.chan))
    db.commit()

    users = db.execute("select nick from ircusers").fetchall()
    users = [x[0] for x in users]
    seen_users = db.execute(
        'select name, time from seen where chan="%s"' % input.chan
    ).fetchall()

    seen_user_list = [x[0] for x in seen_users]
    # first kick any users who have never spoken
    # i.e. they're not in the seen table
    never_seen_users = set(users) - set(seen_user_list)
    kicked_users = []
    for user in never_seen_users:
        print ">>> kicking %s" % user
        kicked_users.append(user)
        input.kick(user, 'please pipe up!')

    # now kick anyone who hasn't chatted for over a week
    one_week_ago = datetime.now() - timedelta(weeks=1)
    # then ban anyone who hasn't chatted for over two weeks
    two_weeks_ago = datetime.now() - timedelta(weeks=2)
    # mapping of nick -> datetime they were last seen
    seen_map = {x[0]: datetime.fromtimestamp(x[1])
                for x in seen_users}
    for nick, date in seen_map.items():
        if date < one_week_ago:
            print ">>> %s hasn't chatted in over a week" % nick
            input.kick(nick, 'please pipe up!')
            kicked_users.append(nick)
        elif date < two_weeks_ago:
            print ">>> %s hasn't chatted in over 2 weeks" % nick
            input.ban(nick)
            kicked_users.append(nick)

    # remove any kicked users from the db
    for user in kicked_users:
        db.execute(
            'delete from ircusers where nick="%s"' % user)

    db.commit()


@hook.command
def seen(inp, nick='', chan='', db=None, input=None):
    ".seen <nick> -- Tell when a nickname was last in active in irc"

    inp = inp.lower()

    if input.conn.nick.lower() == inp:
        # user is looking for us, being a smartass
        return "You need to get your eyes checked."

    if inp == nick.lower():
        return "Have you looked in a mirror lately?"

    db_init(db)

    last_seen = db.execute("select name, time, quote from seen where"
                           " name = ? and chan = ?", (inp, chan)).fetchone()

    if last_seen:
        reltime = timesince.timesince(last_seen[1])
        if last_seen[0] != inp.lower():  # for glob matching
            inp = last_seen[0]
        if last_seen[2][0:1] == "\x01":
            return '%s was last seen %s ago: *%s %s*' % \
                (inp, reltime, inp, last_seen[2][8:-1])
        else:
            return '%s was last seen %s ago saying: %s' % \
                (inp, reltime, last_seen[2])
    else:
        return "I've never seen %s" % inp
