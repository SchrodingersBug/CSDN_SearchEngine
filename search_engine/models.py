from __future__ import unicode_literals
from django.db import models

# Create your models here.


class CSDNBlog(models.Model):
    url = models.CharField(max_length=200)
    title = models.CharField(max_length=100)
    writer = models.CharField(max_length=30)
    writer_id = models.CharField(max_length=30)
    read_count = models.IntegerField()
    content = models.TextField()
    date = models.DateField(auto_now=True)


class Query(models.Model):
    query = models.CharField(max_length=100)
    date = models.DateTimeField('date searched')



