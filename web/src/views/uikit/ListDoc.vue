<script setup>
import { onMounted, ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import Dialog from 'primevue/dialog';



import axios from 'axios';

const APIURL = window.apiUrl

const toast = useToast();
const src = ref(null);
const search_image = ref('');
const query_text = ref('');
const images_list = ref([]);
const visible_delete = ref(false);
const visible_update = ref(false);

onMounted(() => {

});

function getSeverity(product) {
    switch (product.inventoryStatus) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warning';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return null;
    }
}

function convertBlobToBase64(blobURL) {
    // 使用 fetch 获取 Blob 对象
    return fetch(blobURL)
        .then(response => response.blob())  // 将响应转换为 Blob
        .then(blob => {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64String = reader.result;  // 完整的 Base64 字符串
                    const cleanBase64String = base64String.replace(/^data:image\/[a-zA-Z]+;base64,/, '');  // 去除前缀
                    resolve(cleanBase64String);  // 返回去除前缀后的 Base64 字符串
                };
                reader.onerror = reject;  // 处理错误
                reader.readAsDataURL(blob);  // 将 Blob 转换为 base64
            });
        });
}

function onFileSelect(event) {
    const file = event.files[0];
    const reader = new FileReader();

    reader.onload = async (e) => {
        src.value = e.target.result;
    };

    reader.readAsDataURL(file);

    convertBlobToBase64(event.files[0].objectURL).then(result => { 
        search_image.value =  result
    })
  
}

const show = (type,msg,detail) => {
    toast.add({ severity: type, summary: msg, detail: detail, life: 3000 });
};

function onUpload(image) {
    // console.log(image)
    convertBlobToBase64(image.files[0].objectURL).then(result => {
        //console.log(result)
        axios.post(APIURL+'/images',{"image":result}, {
        headers: {
        'Content-Type': 'application/json'
    }})
            .then(response => {
                //console.log(response.data.code)
                if(response.data.code === 200) {
                    show('success','Upload Success',response.data.image_id)
                }else {
                    show('danger','Upload Error','')
                }
            
        })
            .catch(error => {
            console.error(error);
        });
        });
    
}

function search() {
    const body = {}
    if (search_image.value != '') {
        body.query_image = search_image.value 
    }
    if (query_text.value != '') {
        body.query_text = query_text.value 
    }
    axios.post(APIURL+'/images/search',body , {
        headers: {
        'Content-Type': 'application/json'
    }})
            .then(response => {
                console.log(response.data.data)
                images_list.value = response.data.data.results
            
        })
            .catch(error => {
            console.error(error);
        });
    
}

const show_delete = () => {
    visible_delete.value = true
}

const show_update = () => {
    visible_update.value = true
}
</script>

<template>
    
    <div class="flex flex-col">
        
        <div class="grid grid-cols-12 gap-8">
        <div class="col-span-full lg:col-span-12">
            <div class="card flex flex-col md:flex-row gap-8" >
                
                    <div class="col-span-full lg:col-span-6 md:w-1/2" >
                        <Textarea v-model="query_text" rows="4" cols="30" type="text" size="large" placeholder="Search Text" style="margin-bottom: 10px;width: 100%;" />
                
                    </div>.
                    <div class="col-span-full lg:col-span-6 md:w-1/2 ">
                        <FileUpload mode="basic" @select="onFileSelect" customUpload auto severity="secondary" accept="image/*"   class="p-button-outlined" />
                        <img v-if="src" :src="src" alt="Image" class="shadow-md rounded-xl w-full sm:w-64" style="filter: grayscale(100%);width: 60px;" />
                    </div>
                    
             
            </div>
            <div class="card flex flex-col md:flex-row gap-8" style="margin-bottom: 10px;margin-top: -80px;">
                <Button label="Search" severity="info" style="width: 100%;" :loading="loading" @click="search" />
                
            </div>
            
            <div class="card flex flex-col md:flex-row gap-8" style="margin-bottom: 10px;margin-top: -30px;">
                <Toast />
                <FileUpload   chooseLabel="Select Images" name="search" @uploader="onUpload" :multiple="false" accept="image/*" :maxFileSize="1000000" customUpload />
        
            </div>
        </div>
    </div>
    <div class="font-semibold text-xl">Images View</div>
        <div class="card" style="display: flex; flex-wrap: wrap; gap: 1rem;">
          
            
            <Card style="width: 25rem; overflow: hidden" v-for="(item, index) in images_list">
                <template #header>
                    <img alt="user header" :src="item.image_path" />
                </template>
                <template #title>{{ item.id }}</template>
                <template #subtitle>score: {{ item.score }}</template>
                <template #content>
                    <p class="m-0">
                        {{ item.description }}
                    </p>
                </template>
                <template #footer>
                    <div class="flex gap-4 mt-1">
                        <Button label="delete" severity="secondary" outlined class="w-full" @click="show_delete" />
                        <Button label="update" class="w-full" @click="show_update"/>
                    </div>
                </template>
            </Card>
        </div>

        
    </div>
    <Dialog v-model:visible="visible_delete" modal header="delete" :style="{ width: '25rem' }">

    </Dialog>

    <Dialog v-model:visible="visible_update" modal header="delete" :style="{ width: '25rem' }">

    </Dialog>
</template>
