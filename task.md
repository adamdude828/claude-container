We have this ability to attempt to scan a project to build a docker file. This is prooving to be to difficult. 

We want to remove and replace with the following. 

This is the container that we will run coding tasks in. 

1. A single image that is based off of https://raw.githubusercontent.com/openai/codex-universal/refs/heads/main/Dockerfile
2. Users have the ability to use this project to store env vars on a project basis that should be stored in .claude-container. 
3. This dockerfile might have an easy way of feeding in versions of certain runtimes. If it does then we should 
give users that same ability with this project. 
4. The ability to add one off commands that will be aded to the container. 
5. The ability to build a cached version of the image. This should have the code included. 


Add all commands as needed. 

Consider where to put files and folders so that we don't have any single file get to big. Generate re-factor to-do's as needed. 