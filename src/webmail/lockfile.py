import warnings
import os
import time
from pathlib import Path


# This module is taken from 
#   - https://gist.github.com/ionrock/3015700
#   - https://github.com/jonasrauber/lockfile

# A file lock implementation that tries to avoid platform specific
# issues. It is inspired by a whole bunch of different implementations
# listed below.

#  - https://bitbucket.org/jaraco/yg.lockfile/src/6c448dcbf6e5/yg/lockfile/__init__.py
#  - http://svn.zope.org/zc.lockfile/trunk/src/zc/lockfile/__init__.py?rev=121133&view=markup
#  - http://stackoverflow.com/questions/489861/locking-a-file-in-python
#  - http://www.evanfosmark.com/2009/01/cross-platform-file-locking-support-in-python/
#  - http://packages.python.org/lockfile/lockfile.html

# There are some tests below and a blog posting conceptually the
# problems I wanted to try and solve. The tests reflect these ideas.

#  - http://ionrock.wordpress.com/2012/06/28/file-locking-in-python/



class LockError(Exception):
    """
    Base class for error arising from attempts to acquire the lock.

    >>> try:
    ...   raise LockError
    ... except Error:
    ...   pass
    """
    def __init__(self, lockfile):
        self.lockfile = lockfile
        super().__init__(f"Could not acquire lock on {lockfile}")


class LockTimeout(LockError):
    """Raised when lock creation fails within a user-defined period of time.

    >>> try:
    ...   raise LockTimeout
    ... except LockError:
    ...   pass
    """
    pass


class AlreadyLocked(LockError):
    """Some other thread/process is locking the file.

    >>> try:
    ...   raise AlreadyLocked
    ... except LockError:
    ...   pass
    """
    pass


class FileLock:
    """A simple locking mechanism based on lockfiles.

    It creates lockfiles and thus works across different processes and
    different machines with access to the same shared file system as
    long as that file system guarantees atomicity for O_CREAT with O_EXCL.

    Args:
        file_or_lockfile: If it has a ".lock" suffix, it is used as is and will
            be truncated, otherwise a ".lock" suffix is appended.
    """

    def __init__(
        self,
        file_or_lockfile
    ):
        lockfile = Path(file_or_lockfile)
        if lockfile.suffix != ".lock":
            lockfile = lockfile.with_suffix(lockfile.suffix + ".lock")
        self.lockfile = lockfile

        self._pid = str(os.getpid()).encode('ascii')
        self._lockfile_fd = None

    @property
    def is_locked(self):
        return self._lockfile_fd is not None

    @staticmethod
    def is_valid_lock(lock_filename):
        """
        See if the lock exists and is left over from an old process.
        """

        try:
            lock_pid = int(open(lock_filename).read())
        except IOError:
            return False
        except ValueError:
            # most likely an empty or otherwise invalid lock file
            return False

        # it is/was another process
        # see if it is running
        try:
            os.kill(lock_pid, 0)
        except OSError:
            return False

        # it is running
        return True

    def acquire(self, timeout=None, interval = 0.05):
        """
        timeout: Number of seconds before a LockTimeout is raised. Can be
            None to disable retrying and instead raise a AlreadyLocked if
            the first attempt fails.
        interval: Number of seconds between each retry."""

        assert not self.is_locked
        start_time = time.time()
        while True:
            mode = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC
            try:
                fd = os.open(self.lockfile, mode)
            except FileExistsError:
                if timeout is None:
                    raise AlreadyLocked(self.lockfile)
                if time.time() - start_time >= timeout:
                    raise LockTimeout(self.lockfile)
                time.sleep(interval)
            else:
                self._lockfile_fd = fd
                os.write(fd, self._pid)

                break

    def release(self):
        if self.is_locked:
            os.close(self._lockfile_fd)
            self._lockfile_fd = None
            try:
                os.remove(self.lockfile)
            except FileNotFoundError:
                warnings.warn(f"{self.lockfile} did not exist anymore")

    def __enter__(self):
        if not self.is_locked:
            self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        self.release()
