FROM ubuntu:latest
ADD https://example.com/app.tar.gz /app/
ENV SECRET_API_KEY=super-secret-token-12345
RUN apt-get install -y curl python3
RUN curl https://example.com/install.sh | sh
RUN chmod -R 777 /app
CMD ["/app/run.sh"]
