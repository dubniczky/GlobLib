Your task is to create a huge dataset of hundreads common linux service / application configuration file paths. There are some examples in the `configuration.yaml` file and that is the file that you need to continue.

We are using glob format, so use * and ** in the paths whenever possible and try to make sure that it applies as broadly as possible without being too broad. Only target linux at this time. for example:
`server.xml` is too broad, it can be anything. `/etc/tomcat2/server.xml` it is too specific because it applies to tomcat version 2, when it's installed in the `/etc` folder.
In these cases include a highly specific path:
- `/etc/tomcat*/server.xml`
and a general one:
- `**/tomcat*/server/xml`
So for versioned entries, always use a wildcard for the version

Another example is `/etc/redis/redis.conf` where the name is specific enough, so `**/redis.conf` is sufficient to always find it, but also include the known full path as a higher certainty match, so if both globs match the path then we can be more certain that we found the right thing. Aim for 1-2 globs on average and 3-4 in rarer more specific cases.

Only include paths that you can validate exists by finding references to it on the internet.
Focus on applications and services that are common on linux systems, try to avoid super niche services
Try to avoid running code locally and work automatically via web requests and writing to the file
Try to avoid built-in config files that are of no interest and the usser usually don't touch themselves such as `/etc/ipsec.conf` and focus on servcies that are later installed or have to be configured to start working

Structure your work as follows:
1. read the `configuration.yaml` and understand the format and examples
2. search on the internet for a batch list of 15-20 of such services and paths
3. add the findings into the globs in the configuration
4. continue with the search