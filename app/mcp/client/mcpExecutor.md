# MCP EXECUTOR

## Description 
Agent dedicated to fulfilling agent requests through tool call execution
Intelligently decides if tool calls are necessary, and if so, what tool to execute and with which parameters
Capable of self correction based on error-causing generated tool arguments
Dedicated for MCP protocol tool execution and exposure
On any given request, a list of MCP servers is given, allowing agents to only expose relevant servers


## Workflow

```txt
               +-----------+                 
               | __start__ |                 
               +-----------+                 
                      *                      
                      *                      
                      *                      
              +------------+                 
              | initialize |                 
              +------------+                 
                      *                      
                      *                      
                      *                      
              +--------------+               
              | getArguments |               
              +--------------+               
              ***          ...               
             *                .              
           **                  ...           
 +-------------+                  .          
 | executeTool |               ...           
 +-------------+              .              
              ***          ...               
                 *        .                  
                  **    ..                   
              +------------+                 
              | validation |                 
              +------------+                 
              ..            ..               
            ..                ..             
          ..                    ..           
+--------------+           +--------------+  
| finalization |           | handleErrors |  
+--------------+           +--------------+  
              **            **               
                **        **                 
                  **    **                   
                +---------+                  
                | __end__ |                  
                +---------+   
```