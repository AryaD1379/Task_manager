"use strict";

// Utility function to clone an object
function clone(obj) { return JSON.parse(JSON.stringify(obj)); }

// Container for everything
var app = {};

// Convenience function to make an item
app.make_task = function() {
    return {
        title: "",
        description: "",
        deadline: null,
        status: "pending"
    };
};

// Convenience function to make set of filters for a query
app.make_filters = function() {
    return {
        // true = descending, false = ascending
        date_created: false,
        deadline: false,
        status: "",
        created_by_self: false,
        assigned_to_self: false,
        created_by_managed_users: false,
        assigned_to_managed_users: false,
        assigned_to_name: false,
        created_by_user: "",
        assigned_to_user: ""
    };
};

// The vue input config object
app.config = {};

// The Vue input setup() function returns the data to be exposed
app.config.setup = function() {
    const tasks = Vue.ref([]);
    const new_task = Vue.ref(clone(app.make_task()));
    const filters = Vue.ref(clone(app.make_filters()));
    const newComment = Vue.ref({});
    const currentTaskComments = Vue.ref([]);
    const currentTaskTitle = Vue.ref("");
    const currentTaskId = Vue.ref(null);
    const isCommentsModalOpen = Vue.ref(false);
    const listOptions = Vue.ref([]); // list of users for assigning task
    const managerList = Vue.ref([]); // list of users to be chosen as managers
    const currentManager = Vue.ref();
    const currentManagerName = Vue.ref('');
    const newManagerId = Vue.ref(null);
    const errorMessage = Vue.ref("");

    // Toggle the date_created filter between true and false    
    // true = descending, false = ascending
    const toggleDateCreated = () => {
        filters.value.date_created = !filters.value.date_created;
        // console.log(filters.value.date_created);
    };

    // Toggle the date_created filter between true and false    
    // true = descending, false = ascending
    const toggleDeadline = () => {
        filters.value.deadline = !filters.value.deadline;
        // console.log(filters.value.deadline);
    };

    const isPopupOpen = Vue.ref(false);
    const editingTask = Vue.ref(clone(app.make_task()));
    let isEditable = Vue.ref(true);
    let isEditableStatus = Vue.ref(true);

    // Send a request to the server to get the tasks
    // Include the filters in the req params to pass to backend
    const applyFilters = () => {
        axios.get("/task_manager/tasks", { params: filters.value })
            .then((res) => {
                console.log("Params: \nDate Created: " + filters.value.date_created);
                console.log("Deadline: " + filters.value.deadline);
                console.log("Status: " + filters.value.status);
                console.log("Created By Self: " + filters.value.created_by_self);
                console.log("Assigned To Self: " + filters.value.assigned_to_self);
                console.log("Created By Managed Users: " + filters.value.created_by_managed_users);
                console.log("Assigned To Managed Users: " + filters.value.assigned_to_managed_users);
                tasks.value = res.data.tasks;
            });
    };

    // POST request to insert the task into the database
    const post_new_task = () => {
        console.log(new_task.value)
        axios.post("/task_manager/task/create", new_task.value).then((res) => {
            //console.log(res.data);
            new_task.value = clone(app.make_task());
            reload();
        });
    };

    const fetchTasks = () => {
        axios.get("/task_manager/tasks", { params: params }).then(function(res){
            tasks.value = res.data.tasks;
        })
    }

    // Fetch the list of users
    const fetchUsers = async () => {
        try {
        const res = await axios.get("/task_manager/users");
        listOptions.value = res.data.map((user) => ({
            label: `${user.first_name} ${user.last_name}`,
            value: user.id,
        }));
        managerList.value  = {...listOptions.value}
        console.log("managerList")
        console.log(managerList)
        } catch (error) {
        console.error("Error fetching users", error);
        }
    };

    // Fetch current manager
    const fetchCurrentManager = async () => {
        try {
            const res = await axios.get("/task_manager/user/current_manager");
            console.log("fetchCurrentManager")
            console.log(res)
            if (res.data.first_name) {
                currentManagerName.value = `${res.data.first_name} ${res.data.last_name}`;
                currentManager.value = res.data.id;
            } else {
                currentManagerName.value = "None";
                console.log("\n\ncurrentManagerName: " + currentManagerName.value + "\n\n");
            }
            console.log("\n\ncurrentManagerName: " + currentManagerName.value + "\n\n");
           

        } catch (error) {
            console.error("Error fetching current manager", error);
        }
    };

    // Change manager
    const changeManager = async (user) => {
        try {
        console.log("in changeManager newManagerId.value: "+newManagerId.value+" user.id "+user.id);
          let resp = await axios.post("/task_manager/user/set_manager", { manager_id: newManagerId.value, user_id: user.id });
          console.log(resp)
            if (resp.data.status === "error") {
                errorMessage.value = resp.data.message;
            } else {
                errorMessage.value = "";
                fetchCurrentManager(); // Update current manager name
            }
        } catch (error) {
            errorMessage.value = "An unexpected error occurred.";
            console.error("Error changing manager", error);
        }
    };

    const isAuthorizedToEdit = async (task, user) => {
        console.log("isAuthorizedToEdit");
    
        // Check if the user is the creator of the task
        if (task.created_by === user.id) {
            console.log("yes " + task.id);
            return true;
        }
    
        // Fetch the manager of the task creator
        const managerId = await fetchManager(task.created_by);
        if (managerId === user.id) {
            console.log("yes, manager " + task.id);
            return true;
        }
    
        console.log("no " + task.id);
        return false;
    };    

    const fetchManager = async (userId) => {
        try {
            let response = await axios.get(`/task_manager/user/get_manager/${userId}`);
            return response.data.manager_id;
        } catch (error) {
            console.error("Error fetching manager", error);
            return null;
        }
    };    

    const isAuthorizedToChangeStatus = (task, user) => {
        console.log("isAuthorizedToChangeStatus")
        if(task.assigned_to === user.id )
        console.log("yes "+task.id)
        else
        console.log("no"+task.id)
        return task.assigned_to === user.id
    };

    const isCEO = (user) => {
        return user.id === 1
    }

    // Edit task functionality
    const editTask = (task) => {
        console.log("in editTask")
        task.assigned_to = task.list
        task.list = null;
        console.log(task)
        axios.post("/task_manager/task/update", task).then((res) => {
            console.log("updated")
            console.log(res.data);
            reload();
        });
        closePopup()
    };
        
    // Post a comment on a task
    const postComment = (task_id) => {
        const comment = newComment.value[task_id];
        if (!comment) return;

        axios.post(`/task_manager/task/comment/${task_id}`, { body: comment })
            .then((res) => {
                if (res.data.status === 'success') {
                    newComment.value[task_id] = '';
                    fetchComments(task_id);
                }
            });
    };

    const fetchComments = (task_id) => {
        axios.get(`/task_manager/task/comments/${task_id}`).then((res) => {
            currentTaskComments.value = res.data.comments;
        });
    };

    const openCommentsModal = (task_id, task_title) => {
        currentTaskId.value = task_id;
        currentTaskTitle.value = task_title;
        fetchComments(task_id);
        isCommentsModalOpen.value = true;
    };

    const closeCommentsModal = () => {
        isCommentsModalOpen.value = false;
        currentTaskId.value = null;
        currentTaskTitle.value = "";
        currentTaskComments.value = [];
    };


    // Refresh the feed without reloading the whole page
    // Will add more dynamic updated items here
    const reload = () => {
        axios.get("/task_manager/tasks").then((res) => {
            tasks.value = res.data.tasks;
        });
    };

    const openPopup = async (task, user) => {
        // Show the popup
        console.log("in openPopup")
        console.log(user)
        isEditable = await isAuthorizedToEdit(task, user)
        isEditableStatus = isAuthorizedToChangeStatus(task, user)
        console.log("isEditable "+isEditable)
        console.log("isEditableStatus "+isEditableStatus)
        editingTask.value = clone(task);
        editingTask.list = '';
        editingTask.value.isEditable = isEditable;
        editingTask.value.isEditableStatus = isEditableStatus;
        console.log("editingTask is")
        console.log(editingTask)
        try {
            const res = await axios.get("/task_manager/users");
            listOptions.value = res.data.map(user => ({
                label: `${user.first_name} ${user.last_name}`, 
                value: user.id
            }));
            console.log(listOptions);
        } catch (error) {
            console.error("Error fetching users", error);
        }

        editingTask.value.deadline = task.deadline.split(' ')[0];
        console.log("editingTask");
        console.log(editingTask);
        isPopupOpen.value = true;
    };

   
    const closePopup = () => {
    // Close the popup
        isPopupOpen.value = false;
    };

    // Initialize data
    fetchUsers();
    fetchCurrentManager();

    return {
        tasks,
        new_task,
        filters,
        newComment,
        currentTaskComments,
        currentTaskTitle,
        currentTaskId,
        isCommentsModalOpen,
        toggleDateCreated,
        toggleDeadline,
        applyFilters,
        post_new_task,
        fetchTasks,
        reload,
        isAuthorizedToEdit,
        isAuthorizedToChangeStatus,
        editTask,
        postComment,
        fetchComments,
        openCommentsModal,
        closeCommentsModal,
        isPopupOpen,
        openPopup,
        closePopup,
        editingTask,
        listOptions,
        managerList,
        currentManagerName,
        newManagerId,
        changeManager,
        isCEO,
        errorMessage
    };
};

// Make the Vue app
app.vue = Vue.createApp(app.config).mount("#app");
app.vue.reload();
