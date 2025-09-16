from django.db import models

class Project(models.Model):
    id_project = models.IntegerField()
    key_project = models.IntegerField()
    nome_project = models.CharField(max_length=100)
    type_project = models.CharField(max_length=50)