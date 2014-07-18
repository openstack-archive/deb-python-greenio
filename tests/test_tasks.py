##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


import greenio
try:
    trollius = None
    import asyncio
    from unittest import TestCase
except ImportError:
    import trollius
    from trollius import From, Return
    asyncio = trollius
    from trollius.test_utils import TestCase


class TaskTests(TestCase):
    def setUp(self):
        asyncio.set_event_loop_policy(greenio.GreenEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop_policy(None)

    if trollius is not None:
        def test_task_yield_from_plain(self):
            @asyncio.coroutine
            def bar():
                yield From(None)
                raise Return(30)

            @asyncio.coroutine
            def foo():
                bar_result = greenio.yield_from(bar())
                return bar_result + 12

            @greenio.task
            def test():
                res = yield From(foo())
                raise Return(res)

            fut = test()
            self.loop.run_until_complete(fut)

            self.assertEqual(fut.result(), 42)

        def test_task_yield_from_exception_propagation(self):
            non_local = {'CHK': 0}

            @asyncio.coroutine
            def bar():
                yield From(None)
                yield From(None)
                1/0

            @greenio.task
            def foo():
                greenio.yield_from(bar())

            @asyncio.coroutine
            def test():
                try:
                    res = yield From(foo())
                    raise Return(res)
                except ZeroDivisionError:
                    non_local['CHK'] += 1

            self.loop.run_until_complete(test())
            self.assertEqual(non_local['CHK'], 1)

        def test_task_yield_from_coroutine(self):
            @asyncio.coroutine
            def bar():
                yield From(None)
                raise Return(5)

            @greenio.task
            def foo():
                return greenio.yield_from(bar())

            fut = foo()
            self.loop.run_until_complete(fut)
            self.assertEqual(fut.result(), 5)
    else:
        exec('''if 1:
        def test_task_yield_from_plain(self):
            @asyncio.coroutine
            def bar():
                yield from []
                return 30

            @asyncio.coroutine
            def foo():
                bar_result = greenio.yield_from(bar())
                return bar_result + 12

            @greenio.task
            def test():
                return (yield from foo())

            fut = test()
            self.loop.run_until_complete(fut)

            self.assertEqual(fut.result(), 42)

        def test_task_yield_from_exception_propagation(self):
            non_local = {'CHK': 0}

            @asyncio.coroutine
            def bar():
                yield
                yield
                1/0

            @greenio.task
            def foo():
                greenio.yield_from(bar())

            @asyncio.coroutine
            def test():
                try:
                    return (yield from foo())
                except ZeroDivisionError:
                    non_local['CHK'] += 1

            self.loop.run_until_complete(test())
            self.assertEqual(non_local['CHK'], 1)

        def test_task_yield_from_coroutine(self):
            @asyncio.coroutine
            def bar():
                yield from []
                return 5

            @greenio.task
            def foo():
                return greenio.yield_from(bar())

            fut = foo()
            self.loop.run_until_complete(fut)
            self.assertEqual(fut.result(), 5)
        ''')

    def test_task_yield_from_invalid(self):
        def bar():
            pass

        if hasattr(asyncio.AbstractEventLoop, 'create_task'):
            err_msg = (r"^greenlet.yield_from was supposed to receive "
                       r"only Futures, got .* in task .*$")
        else:
            err_msg = (r'^"greenio\.yield_from" was supposed to be called '
                       r'from a "greenio\.task" or a subsequent coroutine$')

        @asyncio.coroutine
        def foo():
            with self.assertRaisesRegex(RuntimeError, err_msg):
                greenio.yield_from(bar)

        self.loop.run_until_complete(foo())
