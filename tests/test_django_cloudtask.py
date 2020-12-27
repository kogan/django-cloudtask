# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.test import TestCase

from django_cloudtask import __version__


class DjangoCloudtaskTestCase(TestCase):
    def test_version(self):
        self.assertEqual(__version__, "0.1.0")
