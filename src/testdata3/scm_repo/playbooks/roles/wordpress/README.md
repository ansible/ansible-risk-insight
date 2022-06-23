Ansible role for OpenCraft's landing page
============================================================

This role sets up a Wordpress-based landing page, maintenance page and default page. The service is run behind nginx, and
certbot is used to manage SSL certificates for the landing page.

After deploying new landing page, you need to:
- mount volume with Wordpress data (it can be created from a snapshot),
- change directories `/var/www/*.opencraft.com` to reflect their actual hostnames,
- create new MySQL DB from the dump and set it in `wp-config.php`,
- change hostname of the Wordpress to the correct one in the new DB with `UPDATE opncrft_options SET option_value='https://{{ HOST }}' WHERE option_name = 'siteurl' OR option_name = 'home';`.
