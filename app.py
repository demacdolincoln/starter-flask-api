from flask import Flask, render_template, request, url_for, redirect
import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SelectField
from wtforms import validators
import boto3
from boto3.dynamodb.conditions import Key, Attr
from uuid import uuid4
import dotenv

if os.path.exists(".env"):
    dotenv.load_dotenv(".env")

minicursos = [
    (0, "Primeiros socorros para terapia ocupacional"),
    (1, "Introdução a avaliação abrangente na terapia ocupacional infantil"),
    (
        2,
        "Terapia ocupacional na amamentação: Estratégias para facilitar o desempenho da co-ocupação",
    ),
    (
        3,
        "Intervenções terapêuticas ocupacionais no paciente neurológico adulto e idoso",
    ),
    (4, "terapia ocupacional no domicilio da pessoa idosa"),
    (
        5,
        "experiências sensoriais do ambiente de internamento neonatal na construção do processamento sensorial do RN",
    ),
]

max_participantes = 14

################################################################################
#                                utils                                         #
################################################################################


def search_in_tuple(t, pos, condition):
    for i in t:
        if t[pos] == condition:
            return t[pos]


################################################################################
#                                models                                        #
################################################################################


class ParticipantForm(FlaskForm):
    name = StringField("nome", [validators.InputRequired()])
    email = EmailField("email", [validators.InputRequired()])
    cpf = StringField("cpf", [validators.InputRequired()])
    minicurso = SelectField("minicurso", choices=minicursos)

    def to_dict(self):
        return {
            "name": self.name.data,
            "email": self.email.data,
            "cpf": self.cpf.data,
            "minicurso": int(self.minicurso.data),
        }


class UserForm(FlaskForm):
    password = PasswordField("senha", [validators.InputRequired()])


################################################################################
#                               database                                       #
################################################################################

def access_db():
    dynamodb = boto3.resource("dynamodb", os.getenv("AWS_REGION"))
    return dynamodb.Table(os.getenv("CYCLIC_DB"))


def add_participante(participante):
    db = access_db()
    db.put_item(
        Item={"sk": uuid4().hex, "pk": uuid4().hex, "participante": participante}
    )


def count_minicurso(n):
    db = access_db()
    return db.scan(
        FilterExpression=Attr("participante.minicurso").eq(n), Select="COUNT"
    )["Count"]


def count_all():
    content = []
    for i, j in minicursos:
        content.append((i, j, count_minicurso(i)))
    return content


def list_all():
    db = access_db()
    content = [None] * len(minicursos)
    for i, j in minicursos:
        result = db.scan(FilterExpression=Attr("participante.minicurso").eq(i))
        content[i] = (j, [])

        for p in result["Items"]:
            content[i][1].append(p['participante'])
    return content


################################################################################
#                                  view                                        #
################################################################################

app = Flask(__name__)
app.config["SECRET_KEY"] = uuid4().hex


@app.route("/", methods=["GET", "POST"])
def index():
    parcial_inscritos = count_all()
    form = ParticipantForm()
    if request.method == "POST" and form.validate():
        selected = form.minicurso.data
        if parcial_inscritos[int(selected)][2] >= max_participantes:
            return render_template(
                "index.html",
                form=form,
                parcial_inscritos=parcial_inscritos,
                max_participantes=max_participantes,
                message="máximo de participantes atingido, escolha outro minicurso.",
            )

        else:
            add_participante(form.to_dict())
            return redirect(url_for("sucesso"))

    return render_template(
        "index.html",
        form=form,
        parcial_inscritos=parcial_inscritos,
        max_participantes=max_participantes,
    )

@app.route("/sucesso")
def sucesso():
    return render_template("sucesso.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    form = UserForm()
    if request.method == "POST" and form.validate():
        if form.password.data == os.getenv("password"):
            return redirect(url_for("inscritos"))
    return render_template("login.html", form=form)


@app.route("/inscritos")
def inscritos():
    all_participants = list_all()
    return render_template("inscritos.html", all_participants=all_participants)
