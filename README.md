# Under the Shadow of Grima

A Fire Emblem fangame made in the [Lex Talionis engine](https://gitlab.com/rainlash/lt-maker). Based on the events of Fire Emblem Awakening.

# Directory Structure and Git Pulling from Upstream
This project includes the entire LT engine in the subfolder `lex-talionis`. How you can use Git to manage this is a bit confusing.

On your local computer, you probably have this current Github URL set up as a remote, probably named `origin`. I've set up a second remote, named `upstream`, to point at the LT Gitlab URL. You can check this with `git remote -v`, which lists out all of your remotes. If you don't have the LT Gitlab as a remote, you can add it with:

```
git remote add -m master upstream git@gitlab.com:rainlash/lt-maker.git
```

Don't ever `git pull` directly from there, though, because we need to put it into a subdirectory! You can do that with `git subtree pull` instead:

```
git subtree pull --prefix lex-talionis upstream master --squash
```

(With `--squash`, all of this comes over as a single squashed commit; otherwise, you'll get every commit that happened in the LT engine repository as a separate commit, which would pollute the commit log of this project.)

If I ever end up doing engine hacking (i.e. any edits to anything in the `lex-talionis` folder), this might cause merge conflicts that I'll have to muck about with and attempt to resolve. But that's a Future Me problem, if even that; I haven't decided on if I want to do engine hacking or not.