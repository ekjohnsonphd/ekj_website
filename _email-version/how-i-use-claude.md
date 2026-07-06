# How I use Claude

## Quick intro

I put these notes together to share what I've learned so far using Claude for my research work. This is intended to be a simple overview of my own experience, in case its a helpful reference. Take everything with a grain of salt and know that things move fast enough that some of the content may be out of date.

The best way to figure out how to use Claude is to experiment yourself. My suggestions are a good place to get started, but anything I suggest — when to build a skill and when not to, etc. — is something you should test out yourself and figure out your preferences. All of the tools are so flexible and easy to build upon that they can and should be heavily tailored to what you like and how you work. It's easier to learn from experimentation than it is to try to adopt someone else's stuff directly.

## My preferences and opinions

**My style with Claude:**

I like to micromanage Claude. I like to be able to see what it's doing, decide what changes I want it to make and what I don't want, and I want to be able to audit what it's done in the past. When I started out I was heavier handed with my oversight, and over time I've learned where I want to fully approve each step, where I want something to run and I'll verify later, etc. A lot of my setup is constructed so that I can have as much oversight as I want into what it does.

**What I use where:**

- I use chat when I want to do brainstorming and have back and forth. I also find it to be better at helping with writing tasks.
- I use Claude Code for most of my work, even non-coding work.
  - I prefer to do this in Positron, and to use the Claude extension to interface with Claude. I like this format because Positron can show me my entire directory, and it's easy to see what Claude is changing or referencing and from where. I also have Claude commit changes it makes to my files, and Positron makes it easy to see the version history. The extension is also nice because it has buttons instead of requiring you to know commands on the terminal.
  - I think there may be some advanced functions that are easier to do in a terminal, but this hasn't been an issue for me.
  - The desktop Claude app doesn't show your files or git history.
- I also use cowork sometimes, but it's not my favorite. Anecdotally, cowork is harder for me to micro-manage. Less input at the beginning than what I do with code means that I end up needing to correct more things with cowork, and since it's not as nice for back-and-forth as chat this tends to be more frustrating for me. Additionally, cowork has access to your files in a directory but in a way that's harder for me to follow what changed than code. Generally I only use it in two cases:
  1. When I need a specific tool. For example, I used cowork for some steps of building a conference poster since you can link it with PowerPoint. Code and chat can't do this.
  2. When I want something built that I know I don't need to oversee. For example, I had a 400-page report in Danish that I needed translated into English and converted to an easier format to reference. I didn't need oversight in these steps.

**My shorthands:**

The tooling with Claude can be confusing, but the underlying system is simpler than all the terminology makes it sound. For example, a project in cowork is the same thing as a directory where you have opened Claude Code. It's useful to keep in mind a few underlying rules about the system:

1. Claude likes markdown. Markdown is a simple, readable format of text files. Markdown is its preferred style of communication.
2. Many different tools are just markdown files under the hood. For example, a skill is just a markdown file with a naming convention stored in a folder where Claude knows to find it. When Claude Code writes a plan (or cowork makes itself a todo list), these are markdown files that it saves somewhere in the internal system. Launching an agent is often just opening a new Claude session in the background, and giving it a markdown file with instructions.
3. Most forms of "context" are just folders under the hood. In Code, Claude is able to read and modify anything within the directory you open it in. In cowork, a project is also just a folder Claude can read/write to.
   1. Chat context is the weirdest here, in that the Projects in chat do not correspond to a folder anywhere in your computer. For this reason, it can often be easier to use Code or cowork when you need to give a lot of context or when the context changes over time.

## References

- **Scott Cunningham, [Scott's Mixtape Substack — Claude Code series](https://causalinf.substack.com/s/claude-code).** Practical tutorials on using Claude Code for causal inference and applied econometrics. The Claude Code lecture (#49) is the most useful single entry point.
- **Isaiah Andrews, [Notes on AI for economics PhD students](https://economics.mit.edu/sites/default/files/2026-04/IA%20AI%20note_1.pdf) (MIT, April 2026).** Short PDF; Andrews's advice on how PhD students in economics should think about AI in their research.
- **Ruben Hassid, [How to AI](https://ruben.substack.com/).** Substack newsletter focused on concrete AI workflows with exact prompts and screenshots. General-purpose rather than econ-specific.
- **Pedro H. C. Sant'Anna, [My Claude Code Workflow](https://psantanna.com/claude-code-my-workflow/workflow-guide.html).** End-to-end workflow guide from an econometrician (co-author of the Callaway/Sant'Anna DiD estimator). Worked examples and project setup.

## For beginners: things to try

1. **Do the basic personalization.** This happens in 3 places:
   1. **For chat:** in Settings > General > Instructions for Claude. ([example](claude-examples/personal-info.md))
   2. **For code:** in `~/.claude/CLAUDE.md`. ([example](claude-examples/global-CLAUDE.md))
   3. **For cowork:** in Settings > Cowork > Global instructions. I didn't know about this spot until today, so no example to share.

   Personalization is useful to keep Claude from wasting your time. If you know statistics, telling Claude this will teach it to tell you about a modeling method in terms of the underlying stats. If you prefer data.table over dplyr in R, tell Claude so it will write code the way you want to see it.

   For me, these places are also where I remind Claude how I want oversight and when. For example, telling Claude not to write something unless I tell it to allows me to decide when I want to be the one making the first draft.

   Also a good place to tell it not to be sycophantic.

2. **(For code) Try setting up a Claude Code instance in one of your projects.** Here's how to do this in Positron:
   1. Open a Window in Positron in an existing project folder.
   2. Make sure you've installed the Claude extension. If you have, you can open Claude by clicking on the logo in the top right section of the Positron pane.
   3. Have it generate a project-specific CLAUDE.md. Here's an example prompt I might use to do that: *"Read through this project — the code, the data files, the README, and any notes you can find — and draft a CLAUDE.md for it. I want sections for: project overview and research question, data sources and where they live, key files and what they do, sample restrictions, current status, and any conventions I should remind you of. Ask me questions about anything you're not sure about before writing it, and flag anything you couldn't figure out from the files."* You can also see an [example project-specific CLAUDE.md here](claude-examples/project-CLAUDE.md).

3. **(For code) Try out Plan Mode with a larger request.**
   1. Example: "I'm building a set of validation plots on the newest set of data. I want multiple types of plots, and I want to compare this set of data to the previous release and to evaluate trends over time. Ask me at least 5 questions about my request and the format I want the files in. Then generate a plan in a markdown file in this directory so I can make edits."
   2. Note that this will work better if you've already done step 2, and Claude can reference CLAUDE.md in the project to know where to find the data and what the columns mean.

4. **(For code) Start experimenting with markdown files.** Maybe you want a data dictionary markdown file so Claude can understand your data better when you reference it. Maybe you have a writing style guide where you tell it how you'd like it to write.
   1. The first advantage of this is that you can give long, detailed instructions to Claude in a persistent way. If you have Claude draft the markdown, you can make edits easier than going back and forth in a chat.
   2. Over time, markdown instructions that you reuse many times are good candidates to become skills.
   3. Markdown instructions are a jumping off point for multi-agent workflows (e.g. an agent to generate content and a second to review).

---

*Last updated: May 2026. Tools change fast; some of this will be out of date by the time you read it.*
