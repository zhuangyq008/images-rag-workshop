<script setup>
import { ref } from 'vue';
import axios from 'axios';
import { onMounted } from 'vue';

const APIURL = window.apiUrl


const list = ref([]);
const answer = ref(null);
const loading = ref(true);

function getList() {
    list.value = []
    axios.post(APIURL+'/analysis_details',{category_id:localStorage.getItem('dataSetId')}, {
    headers: {
    'Content-Type': 'application/json'
  }})
        .then(response => {
            // console.log(response)
        list.value = JSON.parse(response.data.body);
    })
        .catch(error => {
        console.error(error);
    });
}

function analysis(question) {
    answer.value = ""
    loading.value = false
    const json_str = JSON.stringify({"question" : question})
    axios.post(APIURL+'/qa_bot' ,{ body : json_str}, {
    headers: {
    'Content-Type': 'application/json'
  }})
        .then(response => {
            // console.log(response)
        loading.value = true
        answer.value = JSON.parse(response.data.body).answers;
        
    })
        .catch(error => {
        console.error(error);
    });
}

onMounted(() => {
    list.value = getList();
});

</script>

<template>
    <div class="flex flex-col">
        <div class="card">
           
            <Toolbar>
                <!-- <template #start>
                    <Button icon="pi pi-plus" class="mr-2" severity="secondary" text />
                   
                    <Button icon="pi pi-upload" severity="secondary" text />
                </template> -->

                <template #center>
                    <IconField style="width: 100%; min-width: 600px;">
                        <InputIcon >
                            <i class="pi pi-search" />
                        </InputIcon>
                        <InputText placeholder="Please enter your question" size="large" style="width: 100%;" v-model="ana_value"/>
                    </IconField>
                </template>

                <template #end> <Button label="Start analysis"  size="large" @click="analysis(ana_value)" ></Button></template>
            </Toolbar>
        </div>

        <div class="flex flex-col">
            <div >
                <div class="card">
                    <div class="font-semibold text-xl ">
                        Analysis conclusion
                    </div>
                    {{answer}}<i class="pi pi-spin pi-spinner" style="font-size: 2rem" v-if="!loading"></i>
                </div>
                <div class="card">
                    <div class="font-semibold text-xl " style="margin-bottom: 20px;">
                        
                        Comment list
                    

                    </div>
                    <ul class="list-none p-0 m-0" style="height: 800px;overflow-y: scroll;">

                        <li class="flex flex-col md:flex-row md:items-center md:justify-between mb-6" v-for="item in list" :key="item.id" >
                            <Card style="width: 100%;">
                                <template #title>User: {{item.customer}}Rating: {{item.rating}}</template>
                                <template #content>
                                    <p class="m-0">
                                        {{item.review}}
                                    </p>
                                    <div style="padding: 10px;">
                                        <Tag severity="success" v-for="tags in item.advantages" :key="item.id" style="margin: 10px;"> 
                                            <span class="text-base">{{tags.term}} </span>
                                        </Tag>
                                        <Tag severity="info" v-for="tags in item.expectations" :key="item.id" style="margin: 10px;"> 
                                            <span class="text-base">{{tags.term}} </span>
                                        </Tag>
                                        <Tag severity="warn" v-for="tags in item.motivations" :key="item.id" style="margin: 10px;"> 
                                            <span class="text-base">{{tags.term}} </span>
                                        </Tag>
                                        <Tag severity="danger" v-for="tags in item.disadvantages" :key="item.id" style="margin: 10px;"> 
                                            <span class="text-base">{{tags.term}} </span>
                                        </Tag>


                                       
                                </div>
                                </template>
                                
                            </Card>
                           
                        </li>

                
                    </ul>
                    

                    
                </div>
            </div> 
            </div>
    </div>
</template>
