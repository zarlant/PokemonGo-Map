FROM python:2.7

ADD requirements.txt /usr/share/local/pokemon/requirements.txt
RUN pip install -r /usr/share/local/pokemon/requirements.txt

ADD locales /usr/share/local/pokemon/locales
ADD templates /usr/share/local/pokemon/templates
ADD static /usr/share/local/pokemon/static
ADD *.json /etc/pokemon/
ADD *.py /usr/share/local/pokemon/

RUN ln -s /etc/pokemon/config.json /usr/share/local/pokemon/config.json && ln -s /etc/pokemon/credentials.json /usr/share/local/pokemon/credentials.json

EXPOSE 5000

ENTRYPOINT ["python", "/usr/share/local/pokemon/example.py",  "-s", "10", "-H", "0.0.0.0", "-ar", "15", "-u", "zarlant", "-p", "r$IC&jzQAl8GNk2", "-l"]

CMD ["Seattle, WA"]