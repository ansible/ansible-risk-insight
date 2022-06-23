# Certificate Manager

This role installs the Certificate Manager which handles obtaining TLS certificates
from LetsEncrypt, and then putting them into Consul so that the HAProxy Load Balancers
can utilize consul-template to render a certificate file from the KV path this component
fills.
