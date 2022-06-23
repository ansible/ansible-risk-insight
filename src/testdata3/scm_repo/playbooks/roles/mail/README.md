# Mail server + Mailman 3

Ansible role for a mail server with a Mailman 3 mailing list.

See [./defaults/main.yml](./defaults/main.yml) for documentation of used variables.

Only tested on Ubuntu 18.04 LTS.

All postfix configuration is controlled via templated files in this role,
with no mysql configuration.
So postfix is fully defined by this ansible role.

Mailman3 is also fully configured by this role.
However, user accounts and mailing list configuration are configured manually by either Postorius or `mailman shell`.
This configuration is stored in the postgres database defined by the `MAILMAN_POSTGRES_*` variables.


## Patches

We have started seeing the following errors in our logs. This issue [has been fixed] over a year ago in version 1.3.3
of django-mailman3. However, as Ubuntu has package freezes, we're still using 1.3.2 (Ubuntu 20.04). Upgrading it could
break compatibility with [its dependencies], so we have decided to simply patch the files.
```text
Exception Type: LookupError at /hyperkitty/api/mailman/archive
Exception Value: unknown encoding: iso-8859-8-i
```
There is also a matter of Hyperkitty handling this part, but we haven't tested the most recent versions, so we cannot
confirm whether it requires an upstream fix.

After deploying a new mail instance, apply the following diffs:
```diff
--- a/usr/lib/python3/dist-packages/django_mailman3/lib/scrub.py
+++ b/usr/lib/python3/dist-packages/django_mailman3/lib/scrub.py
@@ -150,21 +150,28 @@ class Scrubber():
         :type filter_html: Bool
         """
         ctype = part.get_content_type()
-        # Get the charset of the message, if not set, try to guess it's value.
-        # When guess is True, it will never return None.
         charset = self._get_charset(part, default=None, guess=False)
-        payload = part.get_content()
-        # get_content can give either bytes or str, based on whether it was
-        # able to decode the payload. If it is str, return it as it is,
-        # otherwise, try to decode it using the guessed charset.
-        if not isinstance(payload, str):
-            decodedpayload = part.get_payload(decode=True)
+        try:
+            payload = part.get_content()
+        except LookupError as e:
+            payload = "Can't retrieve content: {}".format(e)
+        # get_content will raise KeyError if called on a multipart part.  We
+        # never call _parse_attachment() on multipart parts, so that's OK.
+        # We have seen LookupError if the part's charset is unknown, so catch
+        # that and just return a message.
+        # XXX We could try some known charsets, but for now we just punt.
+        #
+        # get_content will return a string for text/* parts, an
+        # EmailMessage object for message/rfc822 parts and bytes for other
+        # content types.  text/* parts will be CTE decoded and decoded per
+        # their declared charset.  Other parts will be CTE decoded.
+        if ctype == 'message/rfc822':
+            # Return message/rfc822 parts as a string.
+            decodedpayload = str(payload)
         else:
-            # It is also a str, just return it as it is.
+            # It is a str or bytes, just return it as it is.
             decodedpayload = payload
         filename = self._get_attachment_filename(part, ctype)
-        if ctype == 'message/rfc822':
-            decodedpayload = str(decodedpayload)
         return (part_num, filename, ctype, charset, decodedpayload)
 
     def _guess_all_extensions(self, ctype):
```

```diff
--- a/usr/lib/python3/dist-packages/hyperkitty/models/email.py
+++ b/usr/lib/python3/dist-packages/hyperkitty/models/email.py
@@ -345,7 +345,10 @@ class Attachment(models.Model):
     def set_content(self, content):
         if isinstance(content, str):
             if self.encoding is not None:
-                content = content.encode(self.encoding, errors='replace')
+                try:
+                    content = content.encode(self.encoding, errors='replace')
+                except LookupError as e:
+                    content = content.encode('utf-8')
             else:
                 content = content.encode('utf-8')
         self.size = len(content)
```

You can use the following commands to apply them:
```bash
patch /usr/lib/python3/dist-packages/django_mailman3/lib/scrub.py mailman.patch
patch /usr/lib/python3/dist-packages/hyperkitty/models/email.py hyperkitty.patch

systemctl restart mailman3
systemctl restart mailman3-web
```

[has been fixed]: https://gitlab.com/mailman/django-mailman3/-/commit/1bd81528fae77904c58c0d3a1c55589a8d5be4f7#a57b5fa91dfe34ebdea371ded5778f8d16d8880d
[its dependencies]: https://packages.ubuntu.com/focal/mailman3-full
