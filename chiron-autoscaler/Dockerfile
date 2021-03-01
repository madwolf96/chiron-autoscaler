FROM python:3.8-slim

RUN useradd --create-home chiron

COPY .netrc /root/

COPY --chown=chiron:chiron ./ /home/chiron/

RUN pip install --no-cache-dir -r /home/chiron/requirement.txt

RUN rm /root/.netrc

USER chiron
