'''
Created on Mar 8, 2012

@author: rcs
'''

import itertools
import os.path
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), *itertools.repeat("..", 3)))

from pox.lib.mock_socket import MockSocket
from pox.lib.ioworker.io_worker import IOWorker
from sts.util.deferred_io import DeferredIOWorker

class DeferredIOWorkerTest(unittest.TestCase):
  @staticmethod
  def call_later(func):
      # call now!
      func()

  def test_not_sent_until_permitted(self):
    i = DeferredIOWorker(IOWorker())
    i.set_receive_handler(self.call_later)
    i.block()
    i.send("foo")
    self.assertFalse(i._io_worker._ready_to_send)
    self.assertFalse(i._send_queue.empty())
    i.unblock()
    self.assertTrue(i._send_queue.empty())
    i._io_worker._consume_send_buf(3)
    self.assertFalse(i._io_worker._ready_to_send)

  def test_not_received_until_permitted(self):
    i = DeferredIOWorker(IOWorker())
    i.set_receive_handler(self.call_later)
    i.block()
    self.data = None
    def d(worker):
      self.data = worker.peek_receive_buf()
    i.set_receive_handler(d)
    i._io_worker._push_receive_data("bar")
    self.assertEqual(self.data, None)
    i.unblock()
    self.assertEqual(self.data, "bar")
    # Now if unblocked, should go through immediately
    # Note: d does not consume the data
    i._io_worker._push_receive_data("hepp")
    self.assertEqual(self.data, "barhepp")

  def test_receive_consume(self):
    i = DeferredIOWorker(IOWorker())
    i.set_receive_handler(self.call_later)
    self.data = None
    def consume(worker):
      self.data = worker.peek_receive_buf()
      worker.consume_receive_buf(len(self.data))
    i.set_receive_handler(consume)
    i.block()
    i._io_worker._push_receive_data("bar")
    self.assertEqual(self.data, None)
    i.unblock()
    self.assertEqual(self.data, "bar")
    # data has been consumed
    i._io_worker._push_receive_data("hepp")
    self.assertEqual(self.data, "hepp")
