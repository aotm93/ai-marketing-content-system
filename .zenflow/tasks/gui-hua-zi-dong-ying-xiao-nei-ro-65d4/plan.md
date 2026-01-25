# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: 16c62578-109e-4468-9be6-095c2a619563 -->

Assess the task's difficulty, as underestimating it leads to poor outcomes.
- easy: Straightforward implementation, trivial bug fix or feature
- medium: Moderate complexity, some edge cases or caveats to consider
- hard: Complex logic, many caveats, architectural considerations, or high-risk changes

Create a technical specification for the task that is appropriate for the complexity level:
- Review the existing codebase architecture and identify reusable components.
- Define the implementation approach based on established patterns in the project.
- Identify all source code files that will be created or modified.
- Define any necessary data model, API, or interface changes.
- Describe verification steps using the project's test and lint commands.

Save the output to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach
- Source code structure changes
- Data model / API / interface changes
- Verification approach

If the task is complex enough, create a detailed implementation plan based on `{@artifacts_path}/spec.md`:
- Break down the work into concrete tasks (incrementable, testable milestones)
- Each task should reference relevant contracts and include verification steps
- Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [x] Step: Implementation
<!-- chat-id: 72e91e6e-acc9-472f-a8b4-2242d9c0be2c -->

Implement the task according to the technical specification and general engineering best practices.

1. Break the task into steps where possible.
2. Implement the required changes in the codebase.
3. Add and run relevant tests and linters.
4. Perform basic manual verification if applicable.
5. After completion, write a report to `{@artifacts_path}/report.md` describing:
   - What was implemented
   - How the solution was tested
   - The biggest issues or challenges encountered

### [x] Step: 线上项目管理配置界面问题
<!-- chat-id: 5a57c603-bbe8-4ef8-b501-970ccaaea004 -->

我们上线在服务器上，完善项目界面有简单的后台管理，同时避免被直接访问，一般我们只有一个人管理查看，预设简单的输入密码登录方式。我们将会直接在后台修改 api 和其他相关的配置。

### [x] Step: 项目部署方式和配置
<!-- chat-id: b928d8c2-4c0d-4a1f-964a-fa4180347a5c -->

我们通过项目推送到github 进行管理，GitHub 会自动触发  我们的zeabur 的服务器进行部署或者更新的方式。确定整个项目符合条件。

### [x] Step: 推送 第一个版本到github
<!-- chat-id: 596cace5-1960-4ffc-a7bf-b4d04fb69e0b -->

推送项目到github, 默认公开 ，名称对应。

### [x] Step: 修改部分问题后重新推送
<!-- chat-id: 451dc6af-05fd-45a3-99dd-b8590e600bd2 -->

我们希望在后台填写 ai api 密匙，和baseurl, 和wordpress 相关
自动构建时就 生成admin_session_secret - 管理员会话密钥

我们环境变量只配置  后台密码和  数据库。

目前会因为环境变量缺失构建失败，修复后重新推送 。

### [ ] Step: wordpress seo 插件配置修改
<!-- chat-id: f4780ad3-8a71-41c9-925e-8e68e6e7d6ef -->

系统默认时其他的seo 插件，但是我们使用 的是 rank math seo 插件 的设置，修改配置后推送
