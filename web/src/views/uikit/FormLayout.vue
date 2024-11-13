<script setup>
import { ref, watch } from 'vue';
import axios from 'axios';
import { onMounted } from 'vue';
import Tabs from 'primevue/tabs';
import TabList from 'primevue/tablist';
import Tab from 'primevue/tab';
import TabPanels from 'primevue/tabpanels';
import TabPanel from 'primevue/tabpanel';
import Button from 'primevue/button';
import { useToast } from 'primevue/usetoast';


const APIURL = window.apiUrl

const previewData = ref(null);

const dataSetId = ref(null);

const peValue = ref(null);

const loading  = ref(null);

const app_loading  = ref(null);

const tags = ref([])

const toast = useToast();

const showSuccess = () => {
    toast.add({ severity: 'success', summary: 'Success Message', detail: 'Apply Tags Success', life: 3000 });
};

function getPreviewData() {
    previewData.value = []
    axios.post(APIURL+'/preview_data',{category_id: localStorage.getItem('dataSetId')}, {
    headers: {
    'Content-Type': 'application/json'
  }})
        .then(response => {
        previewData.value = response.data.body.data
        peValue.value = response.data.body.prompt.system_prompt
    })
        .catch(error => {
        console.error(error);
    });
}

function generateTags() {
    loading.value = true
    axios.post(APIURL+'/generate_tags',{category_id: localStorage.getItem('dataSetId') , "system_prompt": peValue.value}, {
    headers: {
    'Content-Type': 'application/json'
  }})
        .then(response => {
            tags.value= JSON.parse(JSON.parse(response.data.body).tags)
            loading.value = false

    })
        .catch(error => {
        console.error(error);
    });
}

function applyTags() {
    app_loading.value = true
    axios.post(APIURL+'/review_analysis',{category_id: localStorage.getItem('dataSetId') , "system_prompt": peValue.value}, {
    headers: {
    'Content-Type': 'application/json'
  }})
        .then(response => {
            console.log(response)
            localStorage.setItem('tags',  JSON.stringify(tags.value))
            showSuccess()
            app_loading.value = false

    })
        .catch(error => {
        console.error(error);
    });
}

function safeParseJson(str) {
  try {
    
    return JSON.parse(str);
  } catch (error) {
    console.warn('Invalid JSON format:', str);
    return []; 
  }
}

onMounted(() => {
    getPreviewData();
    dataSetId.value = localStorage.getItem('dataSetId') ||  1001
    
    tags.value = safeParseJson(localStorage.getItem('tags') ||  '')

});



watch(dataSetId, (newVal) => {
    localStorage.setItem('dataSetId', dataSetId.value);
    const event = new CustomEvent('localStorageChanged', {
        detail: { newValue: dataSetId.value },
    });
    window.dispatchEvent(event);
    getPreviewData()

});

</script>

<template>
    <Fluid>
        <Tabs v-model:value="dataSetId">
        <TabList >
            <Tab value="1001">Fasion</Tab>
            <Tab value="2001">Cell Phones</Tab>
            <Tab value="3001">Pet Supplies</Tab>
        </TabList>
        <TabPanels>
            <TabPanel value="1001">
                <p class="m-0">
                    <div class="flex flex-col md:flex-row gap-8">
                        <div class="md:w-1/2">
                            <div class="card flex flex-col gap-4">
                                <div class="font-semibold text-xl" >Prompt</div>
                                <FloatLabel>
                                    <Textarea v-model="peValue" rows="15" cols="30" />
                                    <label>Prompt</label>
                                    

                                </FloatLabel>
                                <Button label="Generate Tags"  :loading="loading" @click="generateTags" />

                            </div>
                        
                        </div>
                        <div class="md:w-1/2">
                            <div class="card flex flex-col gap-4">
                                <div class="font-semibold text-xl" >Data Preview</div>
                                
                                <div style="overflow-y: scroll;  height: 360px;">
                                    <li class="flex flex-col md:flex-row md:items-center md:justify-between mb-6" v-for="item in previewData" :key="item.id">
                                        <Card style="width: 100%;">
                                            <template #title>User: {{item.customer}}，Rating: {{item.rating}}</template>
                                            <template #content>
                                                <p class="m-0">
                                                    {{item.review}}
                                                </p>
                                            
                                            </template>
                                            
                                        </Card>
                                    
                                    </li>
                                </div>




                            </div>

                        </div>
                    </div>
                </p>
            </TabPanel>
            <TabPanel value="2001">
                <p class="m-0">
                    <div class="flex flex-col md:flex-row gap-8">
                        <div class="md:w-1/2">
                            <div class="card flex flex-col gap-4">
                                <div class="font-semibold text-xl" >Prompt</div>
                                <FloatLabel>
                                    <Textarea v-model="peValue" rows="15" cols="30" />
                                    <label>Prompt</label>
                                    

                                </FloatLabel>
                                <Button label="Generate Tags" :loading="loading"  @click="generateTags"/>

                            </div>
                        
                        </div>
                        <div class="md:w-1/2">
                            <div class="card flex flex-col gap-4">
                                <div class="font-semibold text-xl" >Data Preview</div>
                                
                                <div style="overflow-y: scroll;  height: 360px;">
                                    <li class="flex flex-col md:flex-row md:items-center md:justify-between mb-6" v-for="item in previewData" :key="item.id">
                                        <Card style="width: 100%;">
                                            <template #title>User: {{item.customer}}，Rating: {{item.rating}}</template>
                                            <template #content>
                                                <p class="m-0">
                                                    {{item.review}}
                                                </p>
                                            
                                            </template>
                                            
                                        </Card>
                                    
                                    </li>
                                </div>

                            </div>

                        </div>
                    </div>
                </p>
            </TabPanel>
            <TabPanel value="3001">
                <p class="m-0">
                    <div class="flex flex-col md:flex-row gap-8">
                        <div class="md:w-1/2">
                            <div class="card flex flex-col gap-4">
                                <div class="font-semibold text-xl" >Prompt</div>
                                <FloatLabel>
                                    <Textarea v-model="peValue" rows="15" cols="30" />
                                    <label>Prompt</label>
                                    

                                </FloatLabel>
                                <Button label="Generate Tags"  :loading="loading" @click="generateTags" />

                            </div>
                        
                        </div>
                        <div class="md:w-1/2">
                            <div class="card flex flex-col gap-4">
                                <div class="font-semibold text-xl" >Data Preview</div>
                                
                                <div style="overflow-y: scroll;  height: 360px;">
                                    <li class="flex flex-col md:flex-row md:items-center md:justify-between mb-6" v-for="item in previewData" :key="item.id">
                                        <Card style="width: 100%;">
                                            <template #title>User: {{item.customer}}，Rating: {{item.rating}}</template>
                                            <template #content>
                                                <p class="m-0">
                                                    {{item.review}}
                                                </p>
                                            
                                            </template>
                                            
                                        </Card>
                                    
                                    </li>
                                </div>




                            </div>

                        </div>
                    </div>
                </p>
            </TabPanel>
        </TabPanels>
    </Tabs>

       

        <div class="flex mt-8">
            <div class="card flex flex-col gap-4 w-full">
                <div class="font-semibold text-xl">Tags
                   
                </div>

                <div class="grid grid-cols-12 gap-8">
                    <div class="col-span-12 lg:col-span-6 xl:col-span-6">
                        <Card style="width: 25rem; overflow: hidden">
                            <template #title>Advantages Tags</template>
                            
                            <template #content>
                                <p class="m-0">
                                    <Chip :label="item.term" style="margin: 10px;" v-for="item in tags.advantages" :key="item.id" />
                                </p>
                            </template>
                        
                        </Card>
                    </div>
                    <div class="col-span-12 lg:col-span-6 xl:col-span-6">
                        <Card style="width: 25rem; overflow: hidden">
                            <template #title>Disadvantages Tags</template>
                            
                            <template #content>
                                <p class="m-0">
                                    <Chip :label="item.term" style="margin: 10px;" v-for="item in tags.disadvantages" :key="item.id" />
                                </p>
                            </template>
                        
                        </Card>
                    </div>
                    <div class="col-span-12 lg:col-span-6 xl:col-span-6">
                        <Card style="width: 25rem; overflow: hidden">
                            <template #title>Expectations Tags</template>
                            
                            <template #content>
                                <p class="m-0">
                                    <Chip :label="item.term" style="margin: 10px;" v-for="item in tags.expectations" :key="item.id" />
                                </p>
                            </template>
                        
                        </Card>
                    </div>
                    <div class="col-span-12 lg:col-span-6 xl:col-span-6">
                        <Card style="width: 25rem; overflow: hidden">
                            <template #title>Motivations Tags</template>
                            
                            <template #content>
                                <p class="m-0">
                                    <Chip :label="item.term" style="margin: 10px;" v-for="item in tags.motivations" :key="item.id" />
                                </p>
                            </template>
                        
                        </Card>
                    </div>
                    <div class="col-span-12 lg:col-span-6 xl:col-span-6">
                        <Button label="Apply Tags"  :loading="app_loading" @click="applyTags" />
                    </div>
                </div>
                

                
            

            </div>
        </div>
    </Fluid>
</template>
