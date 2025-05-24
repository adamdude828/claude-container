We need to run these series of tasks. The focus of these tasks is to build a system to complete our containerized enviornment to run claude. 

We will start with a task. And we will end with a PR. 

At the end of the task you need to present some sort of evidence that the task is completed. 

At the beginning of every task you need to do numerous internet seawrches to make sure you have the right context.  

Definitions: 
host level - Running on the host system build into the cli. 
container level - running in the container running for the task. 


Tasks. 

1. We need to verify that the mounted container can communicate with git. We need to make sure that the container has ~/.ssh mounted. If possiable 
we need the right folder mounted to ensure http url's work as well.  Make a command that will create a file in the work space and commit it to a feature branch. 
Make a static script for now.  Run this on the queue. 
2. Create a place holder for the command to start a task. For now lets ask the user for the name of the branch.  Create the branch and the PR on the host level. For now just use the gh cli on host.
3. Delete script from step 1. We just needed to make sure that the git connection works. Create the command that will start the task. It should prompt for a string that is the task description.
It will start an async task.  The script should receive the prompt and the branch of the feature. Lets try instructing claude code to follow these steps in the prompt. Claude should run with  --dangerously-skip-permissions and do the following. 
    a. check if the branch is created. 
    b. create if it doesn't exist. 
    c. switch to it if it does. 
    d. commit to the branch when done. 